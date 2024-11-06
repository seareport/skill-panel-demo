from seareport_skill import settings


def key_to_name(key):
    return list(settings.VERSIONS.keys())[list(settings.VERSIONS.values()).index(key)]


def name_to_key(name):
    return settings.VERSIONS[name]


def folders_to_models(folders):
    return [
        list(settings.VERSIONS.keys())[
            list(settings.VERSIONS.values()).index(f.split("/")[-1])
        ]
        for f in folders
    ]


def models_to_folders(models):
    return ["./01_obs/model/" + settings.VERSIONS[m] for m in models]


def get_metric_range(metric: str):
    if metric in ["rmse", "rms", "rms_95", "mad", "madp"]:
        range_ = (0, 0.5)
    elif metric in ["bias"]:
        range_ = (-0.2, 0.2)
    elif metric in ["slope"]:
        range_ = (0, 2)
    else:
        range_ = (0, 1)
    return range_
