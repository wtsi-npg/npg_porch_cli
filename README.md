# npg_porch_cli

A command-line client and a simple client library to enable communication
with the [npg_porch](https://github.com/wtsi-npg/npg_porch) JSON API.

Provides a Python script, `npg_porch_client`, and a Python client API.

NPG_PORCH_TOKEN environment variable should be set to the value of either
the admin or project-specific token. The token should be pre-registered in
the database that is used by the npg_porch API server.

Can be deployed with pip or poetry in a standard way.

Example of using a client API:

``` python
 from npg_porch_cli.api import PorchRequest
 
 pr = PorchRequest(porch_url="https://myporch.com")
 response = pr.send(action="list_pipelines")
```

By default the client is set up to validate the server's CA certificate.
If the server is using a custom CA certificate, set the path to the certificate.

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

If using the client API directly from Python, a dictionary should be used.

``` python
 from npg_porch_cli.api import PorchRequest
 
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
