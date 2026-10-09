"""Client inventory: aliases are alternatives, nested JARs are loader candidates."""

from nostalgia.modcheck.model import ModArchive, ModDescriptor


def client_descriptors(archive: ModArchive) -> tuple[ModDescriptor, ...]:
    return tuple(mod for mod in archive.descriptors if mod.environment != "server")


def version_choices(archives: tuple[ModArchive, ...]) -> dict[str, tuple[str, ...]]:
    direct: dict[str, list[ModDescriptor]] = {}
    aliases: dict[str, list[ModDescriptor]] = {}
    for archive in archives:
        for mod in client_descriptors(archive):
            direct.setdefault(mod.mod_id, []).append(mod)
            for alias in mod.provides:
                aliases.setdefault(alias, []).append(mod)
    choices = {}
    for mod_id in direct.keys() | aliases.keys():
        candidates = direct.get(mod_id) or aliases[mod_id]
        roots = [mod for mod in candidates if not mod.embedded]
        choices[mod_id] = tuple(dict.fromkeys(mod.version_number for mod in roots or candidates))
    return choices
