# npg_porch_cli

A command-line client and a simple client library to enable communication
with the [npg_porch](https://github.com/wtsi-npg/npg_porch) JSON API.

Provides a Python script, `npg_porch_client`, and a Python client API.

NPG_PORCH_TOKEN environment variable should be set to the value of either
the admin or project-specific token. The token should be pre-registered in
the database that is used by the `porch` API server.

The project can be deployed with pip or poetry in a standard way.

Example of using a client API:

``` python
 from npg_porch_cli.api import PorchRequest

 pr = PorchRequest(porch_url="https://myporch.com")
 response = pr.send(action="list_pipelines")

 pr = PorchRequest(
    porch_url="https://myporch.com",
    pipeline_name="Snakemake_Cardinal",
    pipeline_url="https://github.com/wtsi-npg/snakemake_cardinal",
    pipeline_version="1.0",
 )
 response = pr.send(
    action="update_task",
    task_status="FAILED",
    task_input={"id_run": 409, "sample": "Valxxxx", "id_study": "65"},
 )
```

By default the client validates the certificate of the server's certification
authority (CA). If the server's certificate is signed by a custom CA, set the
`SSL_CERT_FILE` environment variable to the path of the CA's certificate.
Python versions starting from 3.11 seem to have increased security precautions
when validating certificates of custom CAs. It might be necessary to set the
`REQUESTS_CA_BUNDLE` environmental variable, see details
[here](https://requests.readthedocs.io/en/latest/user/advanced/#ssl-cert-verification).

``` bash
 export NPG_PORCH_TOKEN='my_token'
 export SSL_CERT_FILE=/path_to/my.pem
 npg_porch_client list_pipelines --base_url https://myporch.com
```

It is possible, but not recommended, to disable this validation check.

``` bash
 export NPG_PORCH_TOKEN='my_token'
 npg_porch_client list_pipelines --base_url https://myporch.com --no-validate_ca_cert
```

A valid JSON string is required for the `--task_json` script's argument, note
double quotes in the example below.

``` bash
 export NPG_PORCH_TOKEN='my_token'
 npg_porch_client update_task --base_url https://myporch.com \
   --pipeline Snakemake_Cardinal \
   --pipeline_url 'https://github.com/wtsi-npg/snakemake_cardinal' \
   --pipeline_version 1.0 \
   --task_json '{"id_run": 409, "sample": "Valxxxx", "id_study": "65"}' \
   --status FAILED
```

The task definition JSON can also be provided via a file name.

```bash
npg_porch_client ... --task_file task.json
```
