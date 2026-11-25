"""
Standardise a download with its dataset's adaptor.

    python -m cnsp_datasets.standardise.format_dataset li2025 DOWNLOAD_DIR OUT_DIR --adaptor-opt onset=none
"""
import argparse
import ast
from importlib import import_module

from cnsp_datasets import registry

from cnsp_datasets.standardise.flat_sink import FlatSinkV1


def get_adaptor_class(dataset_name):
    """Return the ADAPTOR of the dataset's adaptor module (`<package>.<dataset_name>.adaptor`)."""
    module_path = registry.adaptor_module(dataset_name)  # also searches $CNSP_DATASET_PACKAGES
    mod = import_module(module_path)

    try:
        adaptor = getattr(mod, "ADAPTOR")
    except AttributeError as e:
        raise AttributeError(
            f"Module '{module_path}' does not define ADAPTOR. "
            f"Please ensure that an ADAPTOR sentinel is defined in '{module_path}.py'."
        ) from e

    return adaptor


def parse_adaptor_opt(opt):
    """Parse one `key=value` option; the value is a Python literal where possible (quote it to force a string)."""
    key, sep, value = opt.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"adaptor option {opt!r} is not of the form key=value")
    try:
        return key, ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError):
        return key, value


def format_dataset(
    dataset_name,
    download_dir,
    standardised_dir,
    sinker_handle=FlatSinkV1,
    adaptor_kwargs=None,
):
    """Run the dataset's adaptor (constructed with `adaptor_kwargs`) and save every record with the sink."""
    Adaptor = get_adaptor_class(dataset_name)
    adaptor = Adaptor(download_dir=download_dir, **(adaptor_kwargs or {}))

    sinker = sinker_handle(save_directory=standardised_dir)

    for record in adaptor.parse():
        sinker.save_record(record)

    if hasattr(sinker, "finalize"):
        sinker.finalize()


def main(argv=None):
    """Command-line entry point (see the module docstring)."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dataset")
    p.add_argument("download_dir")
    p.add_argument("standardised_dir")
    p.add_argument("--adaptor-opt", action="append", default=[], type=parse_adaptor_opt,
                   metavar="KEY=VALUE",
                   help="keyword argument for the adaptor constructor (repeatable)")
    args = p.parse_args(argv)
    format_dataset(args.dataset, args.download_dir, args.standardised_dir,
                   adaptor_kwargs=dict(args.adaptor_opt))


if __name__ == "__main__":
    main()
