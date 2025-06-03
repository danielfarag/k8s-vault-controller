from kubernetes import client, watch
import sys
import hvac
import base64

class Secret:
    def __init__(self):
        self.vault_secrets_group = "vault.iti.com"
        self.vault_secrets_version = "v1"
        self.vault_secrets_plural = "vault-secrets"
        self.namespace = "default"
        self.custom_objects_api = client.CustomObjectsApi()
        self.core_v1_api = client.CoreV1Api()
        self.last_applied_secret_name_annotation = f"{self.vault_secrets_group}/last-applied-secret-name"

    def stream(self, k8s_watch_instance: watch.Watch):
        try:
            for event in k8s_watch_instance.stream(
                self.custom_objects_api.list_namespaced_custom_object,
                group=self.vault_secrets_group,
                version=self.vault_secrets_version,
                namespace=self.namespace,
                plural=self.vault_secrets_plural
            ):
                event_type = event['type']
                api_obj = event['object']
                metadata = api_obj.get('metadata', {})
                cr_name = metadata.get('name')
                current_secret_name_in_spec = api_obj['spec'].get('secret')

                
                annotations = metadata.get('annotations', {})
                last_applied_secret_name = annotations.get(self.last_applied_secret_name_annotation)

                if event_type == "DELETED":
                    
                    if last_applied_secret_name:
                        self.delete(last_applied_secret_name)
                    else:
                        self.delete(current_secret_name_in_spec)

                elif event_type == "ADDED":
                    self.create_or_update_secret(api_obj, cr_name, current_secret_name_in_spec)
                    self._update_cr_annotation(cr_name, current_secret_name_in_spec)

                elif event_type == "MODIFIED":
                    if last_applied_secret_name and last_applied_secret_name != current_secret_name_in_spec:
                        self.delete(last_applied_secret_name) 
                        self.create_or_update_secret(api_obj, cr_name, current_secret_name_in_spec) 
                        self._update_cr_annotation(cr_name, current_secret_name_in_spec) 
                    else:
                        self.delete(current_secret_name_in_spec)
                        self.create_or_update_secret(api_obj, cr_name, current_secret_name_in_spec)
                        self._update_cr_annotation(cr_name, current_secret_name_in_spec)

        except Exception as e:
            print(f"Error in stream: {e}", file=sys.stderr)

    def delete(self, secret_name: str):
        try:
            delete_options = client.V1DeleteOptions()
            self.core_v1_api.delete_namespaced_secret(
                name=secret_name,
                namespace=self.namespace,
                body=delete_options
            )
        except client.ApiException as e:
            if e.status == 404:
                print(f"Kubernetes Secret '{secret_name}' not found, nothing to delete.")
            else:
                print(f"Error deleting Kubernetes Secret '{secret_name}' (status {e.status}): {e.reason}", file=sys.stderr)
                if e.body:
                    print(f"Response body: {e.body}", file=sys.stderr)
        except Exception as e:
            print(f"An unexpected error occurred during K8s Secret deletion: {e}", file=sys.stderr)

    def create_or_update_secret(self, api_obj: dict, cr_name: str, secret_name: str):

        try:
            connection = api_obj['spec'].get('connection')
            vault = api_obj['spec'].get('vault')
            
            vault_connection_cr = self.custom_objects_api.get_namespaced_custom_object(
                group=self.vault_secrets_group,
                version=self.vault_secrets_version,
                namespace=self.namespace,
                plural="vault-connections",
                name=connection
            )

            host = vault_connection_cr['spec'].get('host')
            token = vault_connection_cr['spec'].get('token')

            path_parts = vault.split('/')

            mount_point = path_parts[0]
            secret_path = '/'.join(path_parts[1:])

            vault_client = hvac.Client(url=host, token=token)
            
            if not vault_client.is_authenticated():
                print(f"Vault client not authenticated for host '{host}'. Check token.", file=sys.stderr)
                return

            response = vault_client.secrets.kv.v2.read_secret_version(mount_point=mount_point, path=secret_path)

            encoded_secret_data_for_k8s = {}
            for key, value in response["data"]["data"].items():
                encoded_secret_data_for_k8s[key] = base64.b64encode(str(value).encode('utf-8')).decode('utf-8')

            k8s_secret_body  = client.V1Secret(
                api_version="v1",
                kind="Secret",
                metadata=client.V1ObjectMeta(name=secret_name, namespace=self.namespace),
                data=encoded_secret_data_for_k8s
            )

            try:
                self.core_v1_api.create_namespaced_secret(namespace=self.namespace, body=k8s_secret_body)
                print(f"Kubernetes Secret '{secret_name}' created successfully.")
            except client.ApiException as e:
                if e.status == 409: 
                    print(f"Kubernetes Secret '{secret_name}' already exists, replacing it.")
                    self.core_v1_api.replace_namespaced_secret(name=secret_name, namespace=self.namespace, body=k8s_secret_body)
                    print(f"Kubernetes Secret '{secret_name}' replaced successfully.")
                else:
                    print(f"Error creating/replacing Kubernetes Secret '{secret_name}' (status {e.status}): {e.reason}", file=sys.stderr)
                    if e.body:
                        print(f"Response body: {e.body}", file=sys.stderr)
            except Exception as e:
                print(f"An unexpected error occurred during K8s Secret creation/replacement: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error in create_or_update_secret method for CR '{cr_name}': {e}", file=sys.stderr)

    def _update_cr_annotation(self, cr_name: str, new_secret_name: str):
        try:
            patch_body = {
                "metadata": {
                    "annotations": {
                        self.last_applied_secret_name_annotation: new_secret_name
                    }
                }
            }

            
            self.custom_objects_api.patch_namespaced_custom_object(
                group=self.vault_secrets_group,
                version=self.vault_secrets_version,
                namespace=self.namespace,
                plural=self.vault_secrets_plural,
                name=cr_name,
                body=patch_body
            )
            print(f"Updated annotation '{self.last_applied_secret_name_annotation}' on '{cr_name}' to '{new_secret_name}'.")
        except client.ApiException as e:
            print(f"Error patching Custom Resource '{cr_name}' to update annotation (status {e.status}): {e.reason}", file=sys.stderr)
            if e.body:
                print(f"Response body: {e.body}", file=sys.stderr)
        except Exception as e:
            print(f"An unexpected error occurred while updating CR annotation for '{cr_name}': {e}", file=sys.stderr)
