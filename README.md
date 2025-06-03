# Custom Vault Controller for Kubernetes

This project demonstrates a **Proof of Concept (POC)** for a Custom Kubernetes Controller designed to integrate HashiCorp Vault with Kubernetes, allowing you to manage and inject secrets from Vault into your Kubernetes cluster.

## 🌟 Features

  * **Centralized Secret Management:** Leverage Vault as your single source of truth for secrets.
  * **Automated Secret Injection:** Automatically create Kubernetes `Secret` resources from specified Vault paths.
  * **Custom Resources:** Introduces `VaultConnection` and `VaultSecret` Custom Resource Definitions (CRDs) for easy configuration.
  * **Kubernetes Native:** Operates as a native Kubernetes controller, adhering to the Kubernetes API.

-----

## 📺 Video Demonstration

For a visual walkthrough of this custom Vault controller in action, check out the video demonstration:

[Example Vault Controller Video](https://drive.google.com/file/d/1LtDRj7Rhl8g40wk7zm6tOZMQoGQ7tj5A/view?usp=sharing)

-----

### Installation

The controller deployment involves several Kubernetes resources: a `ServiceAccount`, `ClusterRole`, `ClusterRoleBinding`, a `Pod` for the controller itself, and the necessary Custom Resource Definitions (CRDs) for `VaultConnection` and `VaultSecret`.

1.  **Deploy the Controller and RBAC:**
    Apply the provided YAML configuration to your Kubernetes cluster. This will create the `ServiceAccount`, `ClusterRole`, `ClusterRoleBinding`, and the controller `Pod`.

    ```sh
    kubectl apply -f https://raw.githubusercontent.com/DanielFarag/k8s-vault-controller/main/sample/controller.yaml
    ```

2.  **Verify Controller Deployment:**
    Check if the controller pod is running successfully:

    ```sh
    kubectl get pod -l name=vault-controller
    ```

    You should see output similar to this, indicating the pod is `Running`:

    ```
    NAME               READY   STATUS    RESTARTS   AGE
    vault-controller   1/1     Running   0          2m
    ```

-----

## 🛠️ Usage

Once the controller is deployed, you can define `VaultConnection` and `VaultSecret` resources to integrate with your Vault instance.

### 1\. Define a Vault Connection

First, create a `VaultConnection` Custom Resource (CR). This resource holds the necessary information to connect to your Vault instance, including its host and a token.

**Example: `vault-connection.yaml`**

```yaml
apiVersion: vault.iti.com/v1
kind: VaultConnection
metadata:
  name: vault-connection-1
spec:
  host: https://3fe0-197-121-52-47.ngrok-free.app   # Replace with your Vault host
  token: hvs.xxxxxxxxxxxxxxxxxxx                    # Replace with your Vault token (consider using a Kubernetes Secret for production)
```

Apply this configuration to your cluster:

```sh
kubectl apply -f vault-connection.yaml
```

**Important Security Note:** For production environments, it is highly recommended to store your Vault token in a Kubernetes `Secret` and reference it from your `VaultConnection` custom resource, rather than hardcoding it directly in the YAML.

### 2\. Create a Vault Secret

Next, define a `VaultSecret` Custom Resource. This resource links to a `VaultConnection` and specifies the path within Vault from which to retrieve the secret. The controller will then create a Kubernetes `Secret` with the specified name, containing the data from Vault.

**Example: `vault-secret.yaml`**

```yaml
apiVersion: vault.iti.com/v1
kind: VaultSecret
metadata:
  name: vault-secret-11
spec:
  connection: vault-connection-1    # Refers to the VaultConnection created above
  vault: secret/my-app/config       # The path to your secret in Vault
  secret: database-credentials      # The name of the Kubernetes Secret to be created
```

Apply this configuration to your cluster:

```sh
kubectl apply -f vault-secret.yaml
```

-----

### Verification

After applying the `VaultSecret` resource, the controller will read the data from Vault and create a corresponding Kubernetes `Secret`.

You can verify the creation of the Kubernetes `Secret` by running:

```sh
kubectl get secret database-credentials -o yaml
```

The output will show the base64-encoded secret data retrieved from Vault.


-----

## 💡 Future Enhancements (Ideas for POC)
  * **Secret Rotation:** Implement mechanisms for automatic secret rotation.
  * **Error Handling and Status:** Improve error reporting and status updates for `VaultConnection` and `VaultSecret` resources.
  * **Vault Authentication Methods:** Support other Vault authentication methods (e.g., Kubernetes Auth Method).
  * **Namespace Scoping:** Allow `VaultConnection` and `VaultSecret` to be scoped to specific namespaces.