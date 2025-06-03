from kubernetes import config, watch
import sys
import os
from secrets_watcher import Secret  
import asyncio


async def main():
    try:
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            config.load_incluster_config()
            print('Successfully loaded in-cluster Kubernetes configuration.')
        else:
            config.load_kube_config()
            print('Successfully loaded Kubernetes configuration from default kubeconfig.')

        w = watch.Watch()

        secret = Secret()

        secret.stream(w) 

    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())