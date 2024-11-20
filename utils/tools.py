def value_to_key(value, dict_):
    return list(dict_.keys())[list(dict_.values()).index(value)]


def key_to_value(key, dict_):
    return dict_[key]


def folders_to_models(folders, dict_):
    return [
        list(dict_.keys())[list(dict_.values()).index(f.split("/")[-1])]
        for f in folders
    ]


def models_to_folders(models, dict_):
    return ["./01_obs/model/" + dict_[m] for m in models]


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
