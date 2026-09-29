def multi_tier_dict_to_textgrid(data: dict) -> str:
    """
    Convert a dict of tiers into a Praat TextGrid string.

    Parameters
    ----------
    data : dict
        Each key = tier name, value = dict with keys 'item', 'onset_s', 'offset_s',
        all lists of equal length.

    Returns
    -------
    str : TextGrid content in Praat's long text format
    """
    # global xmin/xmax across all tiers
    xmin = min(min(v["onset_s"]) for v in data.values())
    xmax = max(max(v["offset_s"]) for v in data.values())

    lines = []
    lines.append('File type = "ooTextFile short"')
    lines.append('Object class = "TextGrid"\n')
    lines.append(f"xmin = {xmin}")
    lines.append(f"xmax = {xmax}")
    lines.append("tiers? <exists>")
    lines.append(f"size = {len(data)}")
    lines.append("item []:")

    for i, (tier_name, tier) in enumerate(data.items(), 1):
        items = tier["item"]
        onsets = tier["onset_s"]
        offsets = tier["offset_s"]
        assert len(items) == len(onsets) == len(offsets), f"Tier {tier_name} length mismatch"

        lines.append(f"    item [{i}]:")
        lines.append('        class = "IntervalTier"')
        lines.append(f'        name = "{tier_name}"')
        lines.append(f"        xmin = {xmin}")
        lines.append(f"        xmax = {xmax}")
        lines.append(f"        intervals: size = {len(items)}")

        for j, (txt, t0, t1) in enumerate(zip(items, onsets, offsets), 1):
            lines.append(f"        intervals [{j}]:")
            lines.append(f"            xmin = {t0}")
            lines.append(f"            xmax = {t1}")
            lines.append(f'            text = "{txt}"')

    return "\n".join(lines)