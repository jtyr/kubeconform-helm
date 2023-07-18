#!/usr/bin/env python3

import re
import os
import sys

from contextlib import contextmanager

import plugin_wrapper as pw


@contextmanager
def cd(newdir):
    prevdir = os.getcwd()

    os.chdir(os.path.expanduser(newdir))

    try:
        yield
    finally:
        os.chdir(prevdir)


def main():
    # Parse args
    args = pw.parse_args(
        add_chart=False,
        add_files=True,
        add_path=True,
        add_incl_excl=True,
        add_path_sub=True,
    )

    # We gonna change directory into the chart directory so we add it as local
    # path for helm dependency build and helm template
    args["helm_build"].append(".")
    args["helm_tmpl"].append(".")

    # Ger logger
    log = pw.get_logger(
        args["wrapper"].debug,
    )

    # Here we store paths fo the changed charts
    charts = {}

    # Calculate length of the path to the directories with charts
    path_items_lens = [len(x.split(os.sep)) + 1 for x in args["wrapper"].charts_path]

    # Includes and excludes
    if args["wrapper"].include_charts is not None:
        include_charts = list(map(str.strip, args["wrapper"].include_charts.split(",")))
    else:
        include_charts = []

    if args["wrapper"].exclude_charts is not None:
        exclude_charts = list(map(str.strip, args["wrapper"].exclude_charts.split(",")))
    else:
        exclude_charts = []

    for i, charts_path in enumerate(args["wrapper"].charts_path):
        for f in args["wrapper"].FILES:
            if f.startswith("%s%s" % (charts_path, os.sep)):
                # Path substitution if any is defined
                if (
                    args["wrapper"].path_sub_pattern is not None
                    and "," in args["wrapper"].path_sub_pattern
                ):
                    pattern, repl = args["wrapper"].path_sub_pattern.split(
                        args["wrapper"].path_sub_separator, 1
                    )
                    f = re.sub(pattern, repl, f)

                items = f.split(os.sep)
                name = items[path_items_lens[i] - 1]

                # Skip chart if it's not included or is excluded
                if (
                    include_charts and name not in include_charts
                ) or name in exclude_charts:
                    continue

                if len(items) > path_items_lens[i]:
                    path = os.sep.join(items[0 : path_items_lens[i]])

                    if path not in charts:
                        charts[name] = path

    # Change directory to the chart and run tests
    for name, path in charts.items():
        print("Testing chart '%s'" % name)

        with cd(path):
            # Parse config file
            config_args = pw.parse_config(
                args["wrapper"].config,
            )

            # Merge the args from config file and from command line
            if config_args:
                args["kubeconform"] = config_args + args["kubeconform"]

            # Get list of values files
            values_files = pw.get_values_files(
                args["wrapper"].values_dir,
                args["wrapper"].values_pattern,
            )

            # Run tests
            try:
                if values_files:
                    for values_file in values_files:
                        log.debug("Testing with an extra values file %s" % values_file)

                        pw.run_test(args, values_file)
                else:
                    log.debug("Testing without any extra values files")

                    pw.run_test(args)
            except Exception as e:
                log.error("Testing failed: %s" % e)

                sys.exit(1)


if __name__ == "__main__":
    main()
