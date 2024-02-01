#!/usr/bin/env python

import os
import subprocess
import yaml
import json
import base64

print("Please provide the GitLab user/name and password")
username = input("Username: ")
password = input("Password: ")


class DockerConfigJson(object):
    __username: str
    __password: str

    def __init__(self, username: str, password: str) -> None:
        self.__username = username
        self.__password = password

    @property
    def registry(self) -> str:
        return "https://registry.gitlab.com"

    @property
    def __credentials(self) -> dict:
        return {"username": self.__username, "password": self.__password}

    @property
    def __dict__(self) -> dict:
        return {"auths": {self.registry: self.__credentials}}

    def encode(self) -> str:
        data = json.dumps(self.__dict__, default=lambda o: o.__dict__).encode("utf-8")
        return base64.b64encode(data).decode()


class KubernetesDockerSecret(object):
    def __init__(
        self,
        namespace: str,
        name: str,
        secret: DockerConfigJson,
        seal_secret: bool = True,
    ) -> None:
        self.__namespace = namespace
        self.__name = name
        self.__secret = secret
        self.__seal_secret = seal_secret

    @property
    def __dict__(self) -> dict:
        return {
            "apiVersion": "v1",
            "kind": "Secret",
            "type": "kubernetes.io/dockerconfigjson",
            "metadata": {"name": self.__name, "namespace": self.__namespace},
            "data": {".dockerconfigjson": self.__secret.encode()},
        }

    def seal(self, data: str) -> str:
        if self.__seal_secret:
            response = subprocess.run(
                ["kubeseal", "-o", "yaml"],
                input=data.encode("utf-8"),
                stdout=subprocess.PIPE,
            )
            data = response.stdout.decode()

        return data

    def render(self) -> str:
        return self.seal(
            data=yaml.dump(self.__dict__, default_flow_style=False, sort_keys=False)
        )

    def select_cluster(self, profile: str, cluster: str) -> None:
        subprocess.run(
            ["aws", "eks", "update-kubeconfig", "--name", cluster, "--profile", profile],
            stdout=subprocess.PIPE,
        )

    def store(self, filename: str) -> bool:
        filename = os.path.abspath(filename)

        if not os.path.isfile(filename):
            raise FileNotFoundError(f"Could not find the secret file: {filename}")

        with open(filename, mode="w") as fh:
            fh.write(self.render())

        return True


secret = KubernetesDockerSecret(
    name="gitlab-registry-credentials",
    namespace="metabotnik",
    secret=DockerConfigJson(username=username, password=password),
)

secret.select_cluster(cluster="brill-test-hetzner-eks", profile="brill-hetzner-test")

if secret.store(filename="dev/gitlab-registry-credentials.yaml"):
    print("\nGitLab credentials for brill-test-hetzner-eks are updated!\n")

secret.select_cluster(cluster="brill-prod-hetzner-eks", profile="brill-hetzner-prod")

if secret.store(filename="master/gitlab-registry-credentials.yaml"):
    print("\nGitLab credentials for brill-prod-hetzner-eks are updated!\n")
