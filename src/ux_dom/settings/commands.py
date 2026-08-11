# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


"""TailwindCommand and related asset commands."""
import asyncio
import logging
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import cast, Optional, Union

import valio

from ux_dom.settings import WebAssets

__all__ = ["Command", "TailwindCommand"]


logger = logging.getLogger(__name__)


def is_windows():
    if platform.system() == "Windows":
        return True
    if platform.system().startswith("MINGW64_NT-"):
        return True
    return False


IS_WINDOWS = is_windows()


@dataclass
class Command(object):
    # command = valito.StringField(logger=False, debug=True)

    def run_command(self, *cmd, **kw) -> tuple[int, list[str]]:
        # self.command.logger.info(f'# {" ".join(cmd)}')

        if kw.get("shell"):
            while isinstance(cmd, list) or isinstance(cmd, tuple):
                cmd = cmd[0]
            # self.command.logger.debug(f'shell: {cmd}')
        with subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw
        ) as p:
            if not p.stdout:
                raise Exception("fail to popen")
            while p.poll() is None:
                lines = []
                for line_bytes in iter(p.stdout.readline, b""):
                    line_bytes = line_bytes.rstrip()
                    try:
                        line = line_bytes.decode(kw.get("encoding"))
                    except (Exception,):
                        encoding = "utf-8"
                        line = line_bytes.decode(encoding)
                    # self.command.logger.debug(line.rstrip())
                    lines.append(line)
                returncode = p.wait()
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, cmd)
        return p.returncode, lines


# GROUPS = Union[str, list[str], None]


# class GroupValidator(valio.Validator):
#     annotation = GROUPS


# class GroupField(valio.Field):
#     validator = GroupValidator


# @dataclass
# class Group(Command):
#     groups = GroupField(logger=False, debug=True)
#
#     @groups.add_post_validator
#     def groups_as_list(self, group):
#         if isinstance(group, str):
#             return (group,)
#         return group
#
#     def exists(self) -> dict:
#         groups = dict()
#         for grp in self.group:
#             self.groups.logger.info(grp)
#             try:
#                 result = self.run_command('getent', 'group', grp)
#                 groups[grp] = result[1]
#                 self.groups.logger.info(result)
#             except (Exception,) as e:
#                 self.groups.logger.error(e)
#                 groups[grp] = False
#         return groups
#
#     def add(self, name):
#         ...
#
#     def remove(self, name):
#         ...
#
#     group: GROUPS = groups.validator


# TailwindValidator retained for API compatibility (valio field pattern).
class TailwindValidator(valio.Validator):
    annotation = Union[str, list[str], None]


@dataclass
class TailwindCommand(object):
    """Tailwind CLI wrapper.

    On Python 3.14+, dataclass fields need explicit annotations (PEP 649).
    ``tailwindcss`` is a plain str field (default binary name); valio is not
    required for this path.
    """

    file_path: Union[str, Path]
    webassets: WebAssets
    input_css: Optional[Union[str, Path]] = "tailwind.css"
    output_css: Optional[Union[str, Path]] = "styles.css"
    minify: bool = False
    tailwindcss: Union[str, list[str], None] = "tailwindcss"

    def __post_init__(self):
        self.output_css = Path(self.output_css)
        self._root_dir = self.webassets.dir
        self._project_dir = Path(self.file_path).parent
        self._input_file: Path = self._root_dir / self.input_css
        # path of output file is ../assets/../style.css
        self._output_file: Path = self.webassets.static.css / self.output_css

        # this sections of the code is for checking is any old css files exists
        # and if any file exists then delete all older files except the newest one.
        try:
            all_output_files = sorted(
                Path(self.webassets.static.css).glob(f"*{self._output_file.suffix}"),
                reverse=True,
            )

            old_output_file = all_output_files[0]
            if len(all_output_files) > 1:
                [file.unlink(missing_ok=True) for file in all_output_files[1:]]
        except IndexError:
            old_output_file = None
            # here none of the css file exists so we will create it

        if old_output_file:
            self._output_file = self.webassets.static.css / old_output_file
            self.output_css = self._output_file.name
            self._output_file = self._output_file.replace(
                self._output_file.with_name(self.output_css)
            )
        else:
            self._output_file = self.webassets.static.css / self.output_css
            self._output_file.touch()

        self.init_tailwind_project()

    def init_tailwind_project(self):
        """Ensure input/output CSS (+ config when useful) exist.

        Compatible with Tailwind CLI **v3** (``tailwindcss init``) and **v4**
        (no ``init`` subcommand — CSS-first ``@import "tailwindcss"``).
        """
        if not self.is_tailwindcss_available():
            return

        major = self._tailwind_major()
        tailwind_config_js = self._root_dir / "tailwind.config.js"

        if major < 4:
            if not tailwind_config_js.exists():
                logger.info("initialising Tailwindcss Config (v3)")
                self.init_tailwind_config(init_dir=self._root_dir)
            if not tailwind_config_js.exists():
                self._write_default_config_js(tailwind_config_js)
            if not self._input_file.exists():
                self._input_file.write_text(
                    "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
                    encoding="utf-8",
                )
        else:
            # v4: no `init`; write CSS entry and a minimal config only if missing
            if not self._input_file.exists():
                try:
                    rel = self._project_dir.resolve().relative_to(
                        self._root_dir.resolve()
                    )
                    source_globs = f"./{rel.as_posix()}/**/*.{{html,js,py}}"
                except Exception:
                    source_globs = "./**/*.{{html,js,py}}"
                self._input_file.write_text(
                    dedent(f"""\
                        @import "tailwindcss";
                        @source "{source_globs}";
                        """),
                    encoding="utf-8",
                )
            if not tailwind_config_js.exists():
                # optional; many v4 projects are CSS-only
                logger.info("Tailwind v4 detected — skipping `tailwindcss init`")

        if not self._output_file.exists():
            self._output_file.touch()

    def _tw_bin(self) -> str:
        """Resolved tailwindcss CLI path (always str for subprocess)."""
        bin_ = self.tailwindcss
        if isinstance(bin_, (list, tuple)):
            return str(bin_[0])
        if bin_ is None:
            return "tailwindcss"
        return str(bin_)

    def _tailwind_major(self) -> int:
        """Best-effort major version of the tailwindcss CLI (3 or 4)."""
        try:
            proc = subprocess.run(
                [self._tw_bin(), "--help"],
                cwd=str(self._root_dir),
                capture_output=True,
                text=True,
                timeout=15,
            )
            text = (proc.stdout or "") + (proc.stderr or "")
            # v4 help lists `canonicalize` / has no `init` command
            if "canonicalize" in text or "tailwindcss build" in text:
                return 4
            if "init" in text and "content" in text.lower():
                return 3
        except Exception as e:
            logger.debug("tailwind version probe failed: %s", e)
        # pytailwindcss>=0.3 ships v4 by default
        return 4

    def _write_default_config_js(self, path: Path) -> None:
        try:
            content_root = self._project_dir.relative_to(self._root_dir.parent.parent)
        except Exception:
            content_root = Path("..")
        path.write_text(
            dedent(f"""\
                /** @type {{import('tailwindcss').Config}} */
                module.exports = {{
                  darkMode: "class",
                  content: [
                    "../../{content_root}/*.{{html,py}}",
                    "../../{content_root}/**/*.{{html,py}}",
                  ],
                  theme: {{ extend: {{}} }},
                  plugins: [],
                }};
                """),
            encoding="utf-8",
        )

    def is_tailwindcss_available(self) -> bool:
        """Return True only when the tailwindcss binary is on PATH.

        Previous versions returned a ``CompletedProcess`` (always truthy),
        which made missing CLI look installed and broke setup branches.
        """
        output = subprocess.run(
            ["which" if not IS_WINDOWS else "where", self._tw_bin()],
            cwd=str(self._root_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        return output.returncode == 0

    def init_tailwind_config(self, init_dir: Path):
        """Run ``tailwindcss init`` when available (v3). No-op on v4."""
        if self._tailwind_major() >= 4:
            logger.info(
                "tailwindcss v4: `init` not supported — writing defaults in Python"
            )
            return
        logger.info("trying to init tailwindcss config")
        try:
            output = subprocess.run(
                [self._tw_bin(), "init"],
                cwd=str(init_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )
            logger.info(
                "initialisation: returncode=%s stderr=%s",
                output.returncode,
                (output.stderr or "")[:200],
            )
        except Exception as e:
            logger.warning("tailwindcss init failed: %s", e)

    def run(self):
        logger.info(f"cwd: { self._root_dir}")
        logger.info(f"input_file: { self._input_file}")
        logger.info(f"output_file: { self._output_file}")
        try:
            output = subprocess.run(
                [
                    self.tailwindcss,
                    "-i",
                    str(self._input_file.relative_to(self._root_dir)),
                    "-o",
                    str(self._output_file.relative_to(self._root_dir)),
                    f"--{(self.minify and 'minify') or 'watch'}",
                ],
                cwd=str(self._root_dir),
            )
            return output
        except (Exception,) as e:
            logger.error(e)

    async def async_run(self, *, wait: bool | None = None):
        """Run Tailwind CLI.

        * ``minify=True`` (production): one-shot build, await completion.
        * ``minify=False`` (dev watch): start long-lived ``--watch`` process and
          return immediately so HMR / lifespan hooks do not hang on
          ``communicate()``.

        ``wait`` overrides: True always await exit; False never await.
        """
        logger.info(f"cwd: { self._root_dir}")
        logger.info(f"input_file: { self._input_file}")
        logger.info(f"output_file: { self._output_file}")

        one_shot = self.minify if wait is None else wait
        mode_flag = "--minify" if one_shot else "--watch"

        try:
            proc = getattr(self, "_tailwind_process", None)
            if proc is None or proc.returncode is not None:
                self._tailwind_process = await asyncio.create_subprocess_exec(
                    self._tw_bin(),
                    "-i",
                    str(self._input_file.relative_to(self._root_dir)),
                    "-o",
                    str(self._output_file.relative_to(self._root_dir)),
                    mode_flag,
                    cwd=(
                        self._root_dir.as_posix()
                        if not IS_WINDOWS
                        else str(self._root_dir)
                    ),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            if one_shot:
                stdout, stderr = await self._tailwind_process.communicate()
                if stdout:
                    logger.info(f"Output: {stdout.decode(errors='replace')}")
                if stderr:
                    logger.info(f"Error: {stderr.decode(errors='replace')}")
                return self._tailwind_process.returncode

            # watch mode: leave process running for HMR reloader hooks
            logger.info(
                "tailwind --watch started pid=%s (non-blocking)",
                getattr(self._tailwind_process, "pid", None),
            )
            return self._tailwind_process
        except Exception as e:
            logger.error(e)
            raise

    async def async_stop(self):
        """Terminate a long-lived ``--watch`` process if running."""
        proc = getattr(self, "_tailwind_process", None)
        if proc is None or proc.returncode is not None:
            return
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except (asyncio.TimeoutError, ProcessLookupError):
            proc.kill()


#
# if __name__ == "__main__":
#     print(Group(["asdf", "kubctrl"]).exists())
