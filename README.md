# npg_porch_cli

A command-line client and a simple client library to enable communication
with the [npg_porch](https://github.com/wtsi-npg/npg_porch) JSON API.

Provides a Python script, `npg_porch_client`, and a Python client API.

Can be deployed with pip or poetry in a standard way.

Example of using a client API:

``` python
 from npg_porch_cli.api import PorchRequest
 
 pr = PorchRequest(porch_url="https://myporch.com")
 response = pr.send(action="list_pipelines")
```
