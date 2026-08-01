#!/usr/bin/env python3

import errno
import string
import sys
from pathlib import Path

import click
import hs
from asserttool import ic
from asserttool import icp
from clicktool import click_add_options
from clicktool import click_global_options
from clicktool import tvicgvd
from eprint import eprint
from filetool import ensure_line_in_config_file
from globalverbose import gvd
from pathtool import delete_file_and_recreate_empty_immutable
from portagetool import get_latest_postgresql_version
from portagetool import install
from portagetool import set_use_flag_for_package
from proxytool import add_proxy_to_environment
from tmuxtool import in_tmux

_emerge = hs.Command("emerge")
_rc_update = hs.Command("rc-update")
_gpasswd = hs.Command("gpasswd")


def _run(command: hs.Command, *args: str, **kwargs) -> None:
    eprint(command, *args)
    command(*args, _out=sys.stdout, _err=sys.stderr, **kwargs)


def touch_if_new(path: Path) -> None:
    path = Path(path)
    if not path.exists():  # race
        path.touch()


@click.command()
@click.option("--proxy", is_flag=True)
@click_add_options(click_global_options)
@click.pass_context
def cli(
    ctx: click.Context,
    proxy: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
) -> None:
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    _run(hs.Command("dhcpcd"), "eth0", _ok_code=[0, 1])  # 1: already running
    delme = Path("/delme")
    delme.mkdir(exist_ok=True)

    try:
        # it's root:root, let portage recreate it
        Path("/var/db/repos/gentoo").rmdir()
    except OSError as e:
        if e.errno != errno.ENOTEMPTY:
            raise

    # installed by portage-set-emerge-default-opts-on-boot during the chroot
    # phase; run it now so this run's emerges use the options
    if not Path("/etc/portage/emerge_default_opts.conf").exists():
        _run(
            hs.Command("bash"),
            "/etc/local.d/portage_set_emerge_default_opts.start",
        )

    touch_if_new(Path("/etc/portage/cpu_flags.conf"))
    if proxy:
        touch_if_new(Path("/etc/portage/proxy.conf"))

        ensure_line_in_config_file(
            path=Path("/etc/portage/make.conf"),
            line="source /etc/portage/proxy.conf",
            ignore_leading_whitespace=False,
            comment_marker="#",
        )

        add_proxy_to_environment()

    _run(_emerge, "--sync")
    _run(hs.Command("eselect"), "news", "read", "all")

    install("app-misc/tmux")
    install("app-admin/sudo")

    in_tmux()

    install("sys-apps/portage")
    install("net-misc/unison")

    install("dev-build/libtool")  # not sure what for

    install("net-dns/dnscrypt-proxy")
    _run(_rc_update, "add", "dnscrypt-proxy", "default")

    _run(hs.Command("/etc/init.d/dnscrypt-proxy"), "start")
    touch_if_new(Path("/etc/portage/proxy.conf"))
    _run(hs.Command("emaint"), "sync", "-A")

    install("dev-util/debugedit")

    install("app-misc/dodo")
    install("app-misc/echocommand")
    install("app-misc/context-color", force=True)

    install("app-eselect/eselect-repository")
    _run(hs.Command("eselect"), "repository", "enable", "guru")
    _run(hs.Command("emaint"), "sync", "-r", "guru")

    set_use_flag_for_package(package="dev-python/dulwich", flag="-native-extensions")
    install(
        "dev-python/edittool",
        force=True,
    )
    install("net-fs/nfs-utils")
    install("app-misc/mc")
    install("sys-apps/machinesignaturetool", force=True)
    machine_sig = str(hs.Command("machinesignaturetool")()).strip()

    icp(machine_sig)
    ensure_line_in_config_file(
        line=f'MACHINE_SIG="{machine_sig}"',
        path=Path("/etc/env.d/99machine_sig"),
        ignore_leading_whitespace=False,
        comment_marker="#",
    )

    if not Path("/home/user").is_dir():
        _run(hs.Command("useradd"), "--create-home", "user")

    _run(hs.Command("passwd"), "-d", "user")
    install("media-libs/libmtp")  # creates plugdev group
    for _group in (
        "cdrom",
        "cdrw",
        "usb",
        "audio",
        "plugdev",
        "video",
        "render",
        "wheel",
        "dialout",
    ):
        _run(_gpasswd, "-a", "user", _group)

    delete_file_and_recreate_empty_immutable("/home/user/.lesshst")
    delete_file_and_recreate_empty_immutable("/home/user/.vim-session")
    delete_file_and_recreate_empty_immutable("/home/user/.viminfo")
    delete_file_and_recreate_empty_immutable("/home/user/.mupdf.history")
    delete_file_and_recreate_empty_immutable("/home/user/.pdfbox.cache")
    delete_file_and_recreate_empty_immutable("/home/user/.rediscli_history")
    delete_file_and_recreate_empty_immutable("/home/user/unison.log")
    delete_file_and_recreate_empty_immutable("/home/user/tldextract.cache")
    delete_file_and_recreate_empty_immutable("/home/user/.python_history")
    delete_file_and_recreate_empty_immutable("/home/user/Desktop")
    delete_file_and_recreate_empty_immutable("/home/user/opt")

    delete_file_and_recreate_empty_immutable("/root/.lesshst")
    delete_file_and_recreate_empty_immutable("/root/.mupdf.history")
    delete_file_and_recreate_empty_immutable("/root/.pdfbox.cache")
    delete_file_and_recreate_empty_immutable("/root/.rediscli_history")
    delete_file_and_recreate_empty_immutable("/root/unison.log")
    delete_file_and_recreate_empty_immutable("/root/tldextract.cache")
    delete_file_and_recreate_empty_immutable("/root/.python_history")
    delete_file_and_recreate_empty_immutable("/root/Desktop")
    delete_file_and_recreate_empty_immutable("/root/opt")

    install("dev-vcs/git")  # need this for any -9999 packages (zfs)

    for _l in string.ascii_lowercase:
        for _n in string.digits[1:6]:
            Path(f"/mnt/sd{_l}{_n}").mkdir(exist_ok=True)

    for _p in ["loop", "samba", "dvd", "cdrom", "smb"]:
        Path(f"/mnt/{_p}").mkdir(exist_ok=True)

    _run(_rc_update, "add", "netmount", "default")

    install("app-portage/eix")
    _run(hs.Command("chown"), "portage:portage", "/var/cache/eix")
    _run(hs.Command("eix-update"))

    install("dev-db/postgresql")
    pg_version = get_latest_postgresql_version()
    _run(_rc_update, "add", f"postgresql-{pg_version}", "default")
    install("sys-apps/sshd-configurator", force=True)
    _run(hs.Command("perl-cleaner"), "--reallyall")
    _run(_emerge, "-vuDU", "@world")

    _run(_gpasswd, "-a", "root", "lp")
    _run(_gpasswd, "-a", "user", "lp")
    _run(_gpasswd, "-a", "root", "lpadmin")
    _run(_gpasswd, "-a", "user", "lpadmin")

    install("media-sound/alsa-utils")  # alsamixer
    _run(_rc_update, "add", "alsasound", "boot")
    install("media-plugins/alsaequal")
    install("media-sound/alsa-tools")
    _run(hs.Command("chown"), "root:mail", "/var/spool/mail/", _ok_code=[0, 1])  # mail group may not exist
    _run(hs.Command("chmod"), "03775", "/var/spool/mail/")

    install("dev-python/zfstool")
    install("app-editors/neovim")
    _run(_emerge, "--unmerge", "vim")

    eprint("sendgentoo-post-reboot complete")
