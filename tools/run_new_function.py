from contextlib import redirect_stdout, redirect_stderr
import io
import traceback
import inspect

def _build_kwargs(variables):
    call_kwargs = {}
    for item in variables or []:
        if not isinstance(item, dict):
            raise TypeError("Each variable item must be a dict")

        if "name" in item and "value" in item:
            name = item["name"]
            value = item["value"]
        else:
            raise ValueError("Variable dict must contain [name, value]")

        if not isinstance(name, str) or not name:
            raise ValueError("Variable name must be a non-empty string")

        call_kwargs[name] = value

    return call_kwargs


def run_func(function_name: str, function_source: str, variables=None) -> dict:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            namespace = {}
            exec(function_source, namespace)

            function = namespace.get(function_name)
            if function is None or not callable(function):
                raise ValueError(f"Function '{function_name}' not found or not callable")

            call_kwargs = _build_kwargs(variables)

            # Optional: keep this guard to help detect bad parameter mapping early.
            inspect.signature(function).bind(**call_kwargs)

            result = function(**call_kwargs)
        return {
            "ok": True,
            "result": result,
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "error": None,
        }
    except Exception:
        return {
            "ok": False,
            "result": None,
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "error": traceback.format_exc(),
        }

