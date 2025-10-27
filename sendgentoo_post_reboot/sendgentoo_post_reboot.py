#!/usr/bin/env python3
# -*- coding: utf8 -*-
# tab-width:4

from __future__ import annotations

import os
import string
import sys
from pathlib import Path

import click
import sh
from asserttool import ic
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
from proxytool import add_proxy_to_enviroment
from tmuxtool import in_tmux


def syscmd(cmd):
    print(cmd, file=sys.stderr)
    os.system(cmd)


def touch_if_new(path: Path):
    path = Path(path)
    if not path.exists():  # race
        path.touch()


@click.command()
@click.option("--proxy", is_flag=True)
@click_add_options(click_global_options)
@click.pass_context
def cli(
    ctx,
    proxy: bool,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    syscmd("dhcpcd eth0")
    delme = Path("/delme")
    delme.mkdir(exist_ok=True)

    try:
        # it's root:root, let portage recreate it
        Path("/var/db/repos/gentoo").rmdir()
    except OSError as e:
        if e.errno != 39:  # Directory not empty
            raise e

    if not Path("/etc/portage/emerge_default_opts.conf").exists():
        syscmd("bash -c /home/cfg/sysskel/etc/local.d/emerge_default_opts.start")

    touch_if_new(Path("/etc/portage/cpu_flags.conf"))
    # todo
    if proxy:
        touch_if_new(Path("/etc/portage/proxy.conf"))

        ensure_line_in_config_file(
            path=Path("/etc/portage/make.conf"),
            line="source /etc/portage/proxy.conf\n",
            ignore_leading_whitespace=False,
            comment_marker="#",
        )

        add_proxy_to_enviroment()

    syscmd("emerge --sync")
    syscmd("eselect news read all")

    install("app-misc/tmux")
    install("app-admin/sudo")

    in_tmux()

    install("sys-apps/portage")
    install("net-misc/unison")

    install("dev-build/libtool")  # not sure what for

    install("net-dns/dnscrypt-proxy")
    syscmd("rc-update add dnscrypt-proxy default")

    install("dev-python/symlinktree", force=True)
    os.environ["LANG"] = "en_US.UTF8"  # to make click happy
    syscmd("symlinktree /home/cfg/sysskel --verbose-inf")
    syscmd("symlinktree /home/cfg/sysskel --verbose-inf --re-apply-skel /root")

    syscmd("/etc/init.d/dnscrypt-proxy start")
    if not Path("/etc/portage/proxy.conf").exists():
        sh.touch("/etc/portage/proxy.conf")
    syscmd("emaint sync -A")

    install("dev-util/debugedit")

    syscmd("test -h /root/cfg     || { ln -s /home/cfg /root/cfg             ; }")
    syscmd("test -h /root/_myapps || { ln -s /home/cfg/_myapps /root/_myapps ; }")
    syscmd("test -h /root/_repos  || { ln -s /home/cfg/_repos /root/_repos   ; }")

    # done already
    # install("sys-apps/portage-set-cpu-flags-on-boot")

    install("app-misc/dodo")
    install("app-misc/echocommand")
    install("app-misc/context-color", force=True)
    # install('net-dns/dnsgate')
    #
    install("app-eselect/eselect-repository")
    syscmd("eselect repository enable guru")
    syscmd("emaint sync -r guru")

    set_use_flag_for_package(package="dev-python/dulwich", flag="-native-extensions")
    install(
        "dev-python/edittool",
        force=True,
    )
    install("net-fs/nfs-utils")
    install("sys-apps/machinesignaturetool", force=True)
    machine_sig_command = sh.Command("machinesignaturetool")
    machine_sig = machine_sig_command().strip()

    ensure_line_in_config_file(
        line=f'MACHINE_SIG="{machine_sig}"\n',
        path=Path("/etc/env.d/99machine_sig"),
        ignore_leading_whitespace=False,
        comment_marker="#",
    )

    # must be done after symlinktree so etc/skel gets populated
    if not Path("/home/user").is_dir():
        syscmd("useradd --create-home user")

    syscmd("passwd -d user")
    syscmd(
        "symlinktree /home/cfg/sysskel --verbose-inf --re-apply-skel /home/user"
    )  # must be done after /home/user exists

    install("media-libs/libmtp")  # creates plugdev group
    for x in (
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
        syscmd(f"gpasswd -a user {x}")

    syscmd("/home/cfg/setup/fix_cfg_perms")  # must happen when user exists

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

    try:
        if not Path("/home/user/cfg").exists():
            os.symlink("/home/cfg", "/home/user/cfg")
    except FileExistsError:
        pass

    try:
        if not Path("/home/user/_myapps").exists():
            os.symlink("/home/cfg/_myapps", "/home/user/_myapps")
    except FileExistsError:
        pass
    # if not Path("/home/user/_repos").exists():
    #    os.symlink("/home/cfg/_repos", "/home/user/_repos")

    # /home/cfg/git/configure_git_global

    ##if musl is getting used, CHOST must be changed #bug, this is needs to split into it's own conf
    # if [[ "${stdlib}" == "musl" ]];
    # then
    #    echo "setting CHOST to x86_64-gentoo-linux-musl"
    #    /home/cfg/_myapps/replace-text/replace-text --match 'CHOST="x86_64-pc-linux-gnu"' --replacement 'CHOST="x86_64-gentoo-linux-musl"' /etc/portage/make.conf
    # elif [[ "${stdlib}" == "uclibc" ]];
    # then
    #    echo "setting CHOST to x86_64-gentoo-linux-uclibc"
    #    /home/cfg/_myapps/replace-text/replace-text --match 'CHOST="x86_64-pc-linux-gnu"' --replacement 'CHOST="x86_64-gentoo-linux-uclibc"' /etc/portage/make.conf
    # elif [[ "${stdlib}" == "glibc" ]];
    # then
    #    echo -n "leaving CHOST as default glibc"
    #    #grep x86_64-pc-linux-gnu /etc/portage/make.conf || { echo "x86_64-pc-linux-gnu not found in /etc/portage/make.conf, stdlib = ${stdlib}, exiting." ; exit 1 ; }
    # else
    #    echo "unknown stdlib: ${stdlib}, exiting."
    #    exit 1
    # fi
    #
    # if [[ "${stdlib}" == "musl" ]];
    # then
    #    layman -a musl || exit 1
    #    echo "source /var/lib/layman/make.conf" >> /etc/portage/make.conf # musl specific # need to switch to repos.d https://wiki.gentoo.org/wiki/Overlay
    # fi

    install("dev-vcs/git")  # need this for any -9999 packages (zfs)
    # emerge @preserved-rebuild # good spot to do this as a bunch of flags just changed
    # emerge @world --quiet-build=y --newuse --changed-use --usepkg=n

    # emerge-webrsync
    # emerge --sync
    # eselect profile list

    # Path("/etc/local.d/export_cores.start").chmod(0o755)
    # syscmd("/etc/local.d/export_cores.start")

    for _l in string.ascii_lowercase:
        for _n in string.digits[1:6]:
            Path(f"/mnt/sd{_l}{_n}").mkdir(exist_ok=True)

    for _p in ["loop", "samba", "dvd", "cdrom", "smb"]:
        Path(f"/mnt/{_p}").mkdir(exist_ok=True)

    # if [[ "${stdlib}" == "musl" ]];
    # then
    #    install(sys-libs/argp-standalone #for musl
    #    emerge -puvNDq world
    #    emerge -puvNDq world --autounmask=n
    #    emerge -uvNDq world || exit 1 #http://distfiles.gentoo.org/experimental/amd64/musl/HOWTO
    # fi

    syscmd("rc-update add netmount default")

    install("app-portage/eix")
    syscmd("chown portage:portage /var/cache/eix")
    syscmd("eix-update")

    install("dev-db/postgresql")
    pg_version = get_latest_postgresql_version()
    syscmd(f"rc-update add postgresql-{pg_version} default")
    # syscmd(f'emerge --config dev-db/postgresql:{pg_version}')  # ok to fail if already conf
    # sudo su postgres -c "psql template1 -c 'create extension hstore;'"
    # sudo su postgres -c "psql template1 -c 'create extension ltree;'"
    install("sys-apps/sshd-configurator", force=True)
    # emerge --depclean  # unmerges partial emerges, do this after install is known good
    syscmd("perl-cleaner --reallyall")
    syscmd("emerge -vuDU @world")
    # install("@laptopbase")  # https://dev.gentoo.org/~zmedico/portage/doc/ch02.html
    # install("@wwwsurf")
    # install("@webcam")

    # install("@print")
    syscmd("gpasswd -a root lp")
    syscmd("gpasswd -a user lp")
    syscmd("gpasswd -a root lpadmin")
    syscmd("gpasswd -a user lpadmin")

    # lspci | grep -i nvidia | grep -i vga && install(sys-firmware/nvidia-firmware #make sure this is after installing sys-apps/pciutils
    # install(
    #    "sys-firmware/nvidia-firmware"
    # )  # make sure this is after installing sys-apps/pciutils
    # syscmd(
    #    'USE="-opengl -utils" emerge -v1 mesa x11-libs/libva'
    # )  # temp fix the mesa circular dep
    # https://bugs.gentoo.org/602688
    # syscmd('USE="$USE -vaapi" install(@laptopxorg)
    # install("@laptopxorg")

    install("media-sound/alsa-utils")  # alsamixer
    syscmd("rc-update add alsasound boot")
    install("media-plugins/alsaequal")
    install("media-sound/alsa-tools")
    syscmd("chown root:mail /var/spool/mail/")  # invalid group
    syscmd("chmod 03775 /var/spool/mail/")

    # install("@gpib")
    # syscmd("gpasswd -a user gpib")

    ## eselect repository enable science
    ## emaint sync -r science
    ## emerge @gpib -pv
    ## emerge @gpib
    ## gpib_config

    install("dev-python/zfstool")
    install("app-editors/neovim")
    syscmd("emerge --unmerge vim")

    eprint("sendgentoo-post-reboot complete")

    ##echo "vm.overcommit_memory=2"   >> /etc/sysctl.conf
    ##echo "vm.overcommit_ratio=100"  >> /etc/sysctl.conf
    # mkdir /sys/fs/cgroup/memory/0
    ##echo -e '''#!/bin/sh\necho 1 > /sys/fs/cgroup/memory/0/memory.oom_control''' > /etc/local.d/memory.oom_control.start #done in sysskel
    ##chmod +x /etc/local.d/memory.oom_control.start

    # sudo su postgres -c "psql template1 -c 'create extension hstore;'"
    # sudo su postgres -c "psql -U postgres -c 'create extension adminpack;'" #makes pgadmin happy
    ##sudo su postgres -c "psql template1 -c 'create extension uint;'"
