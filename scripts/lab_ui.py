"""
Mission Control: the visual side of the SRE Academy lab game.

render(catalog, progress, xp, level, following) returns one self-contained HTML page (no internet, no tracking):
the story, the student's level and XP, the zone map, every mission card (done / next / open / locked),
achievements and the exact message to type to IBM Bob next. scripts/lab.py writes it to .lab/mission-control.html.
"""

import html

ICONS = {
    "compass": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
    "engine": '<rect x="4" y="7" width="16" height="10" rx="2"/><path d="M8 7V4h8v3M2 12h2M20 12h2M9 12h6"/>',
    "tower": '<path d="M8 21l2-14h4l2 14M7 7h10M12 3v4M9 14h6"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "magnifier": '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1'
            'M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    "flame": '<path d="M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-3 2-4 2-7 1 1 2 2 3 1z"/>',
    "robot": '<rect x="5" y="8" width="14" height="11" rx="2"/><path d="M12 4v4M9 13h.01M15 13h.01M9 16h6"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "check": '<path d="M5 12l5 5 9-10"/>',
}

CSS = """
:root{--bg:#0b1020;--panel:#121a33;--card:#18224a;--line:#26315c;--text:#e8ecff;--muted:#9aa6d6;--accent:#5eead4;
--accent2:#a78bfa;--gold:#fbbf24;--done:#34d399;--lock:#56608c;--radius:14px}
@media (prefers-color-scheme: light){:root{--bg:#f4f6fd;--panel:#ffffff;--card:#eef1fb;--line:#d7ddf3;--text:#141a33;
--muted:#56608c;--accent:#0d9488;--accent2:#7c3aed;--gold:#b45309;--done:#059669;--lock:#9aa3c7}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
header{display:flex;flex-wrap:wrap;gap:20px;align-items:center;justify-content:space-between}
h1{margin:0;font-size:26px;letter-spacing:.3px}h1 span{color:var(--accent)}
.sub{color:var(--muted);margin:4px 0 0}
.level{display:flex;gap:14px;align-items:center;background:var(--panel);border:1px solid var(--line);
border-radius:var(--radius);padding:12px 16px;min-width:300px;flex:1;max-width:460px}
.emblem{width:56px;height:56px;border-radius:50%;display:grid;place-items:center;flex:none;
background:conic-gradient(var(--accent) var(--pct),var(--line) 0)}
.emblem div{width:44px;height:44px;border-radius:50%;background:var(--panel);display:grid;place-items:center;
font-weight:700;color:var(--gold)}
.bar{height:10px;border-radius:99px;background:var(--line);overflow:hidden;margin-top:6px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.story{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;margin:22px 0}
.next{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;margin:0 0 26px;
background:linear-gradient(120deg,color-mix(in srgb,var(--accent) 22%,var(--panel)),var(--panel));
border:1px solid var(--accent);border-radius:var(--radius);padding:18px}
.next h2{margin:0 0 4px;font-size:19px}.next code,.cmd{background:var(--bg);border:1px solid var(--line);
border-radius:8px;padding:6px 10px;font:14px ui-monospace,Consolas,monospace;color:var(--accent);white-space:nowrap}
.zone{margin:26px 0 10px;display:flex;gap:10px;align-items:center}
.zone svg{width:26px;height:26px;stroke:var(--accent2);fill:none;stroke-width:1.8}
.zone h3{margin:0;font-size:17px}.zone p{margin:0;color:var(--muted);font-size:13px}
.zone .count{margin-left:auto;color:var(--muted);font-size:13px;white-space:nowrap}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px;position:relative}
.card .id{font:12px ui-monospace,Consolas,monospace;color:var(--muted)}
.card h4{margin:2px 0 6px;font-size:15px}.card p{margin:0;color:var(--muted);font-size:13px}
.card .xp{position:absolute;top:12px;right:12px;font-size:12px;color:var(--gold);font-weight:700}
.card.done{border-color:var(--done)}.card.done h4::before{content:"\\2713  ";color:var(--done)}
.card.next{border:2px solid var(--accent);box-shadow:0 0 0 4px color-mix(in srgb,var(--accent) 20%,transparent)}
.card.locked{opacity:.55}.card.locked h4::before{content:"\\1F512  "}
.tag{display:inline-block;margin-top:8px;font-size:11px;padding:2px 8px;border-radius:99px;border:1px solid var(--line);
color:var(--muted)}
.badges{display:flex;flex-wrap:wrap;gap:10px}
.badge{display:flex;gap:8px;align-items:center;padding:8px 12px;border-radius:99px;border:1px solid var(--line);
background:var(--panel);font-size:13px}.badge svg{width:18px;height:18px;fill:var(--gold);stroke:none}
.badge.off{opacity:.45}.badge.off svg{fill:var(--lock)}
footer{margin-top:34px;color:var(--muted);font-size:13px}
@media (max-width:640px){.next{grid-template-columns:1fr}.level{min-width:0;max-width:none}}
"""


def _icon(name, cls=""):
    return f'<svg viewBox="0 0 24 24" class="{cls}" aria-hidden="true">{ICONS.get(name, ICONS["star"])}</svg>'


def _md_bold(text):
    """Escape, then turn **bold** into <strong>."""
    parts = html.escape(text).split("**")
    return "".join(f"<strong>{p}</strong>" if i % 2 else p for i, p in enumerate(parts))


def mountain(zones, cleared):
    """SVG of the climb to On-Call Ready: one camp per zone along a winding trail, flags on cleared camps,
    and Bob where he is."""
    n = len(zones)
    w, h = 1000, 340
    points = []
    for i in range(n + 1):  # n camps + the summit
        x = 70 + i * (w - 140) / n
        y = h - 40 - (h - 110) * (i / n) ** 0.9 + (18 if i % 2 else -6) * (1 - i / n)
        points.append((round(x), round(y)))
    trail = " ".join(f"{x},{y}" for x, y in points)
    current = next((i for i, z in enumerate(zones) if z["part"] not in cleared), n)
    parts = [f'<svg viewBox="0 0 {w} {h}" class="peak" role="img" '
             f'aria-label="Bob is at camp {current} of {n} on the climb to On-Call Ready">',
             f'<polygon points="0,{h} 250,190 420,235 930,58 1000,120 1000,{h}" class="m1"/>',
             f'<polygon points="120,{h} 470,215 640,250 930,96 1000,150 1000,{h}" class="m2"/>',
             f'<polyline points="{trail}" class="trail"/>']
    for i, (x, y) in enumerate(points[:-1]):
        zone = zones[i]
        state = "cleared" if zone["part"] in cleared else ("here" if i == current else "ahead")
        parts.append(f'<circle cx="{x}" cy="{y}" r="11" class="camp {state}"/>')
        if state == "cleared":
            parts.append(f'<path d="M{x} {y - 11}v-26l18 7-18 7" class="flag"/>')
        label_y = y + 30 if i % 2 == 0 else y + 48  # two depths below the trail: no collisions, flags stay clear
        parts.append(f'<text x="{x}" y="{label_y}" class="label">{html.escape(zone["name"].replace("The ", ""))}</text>')
    sx, sy = points[-1]
    parts.append(f'<path d="M{sx} {sy - 34}l7 14 15 2-11 10 3 15-14-7-14 7 3-15-11-10 15-2z" '
                 f'class="summit{" reached" if current == n else ""}"/>')
    parts.append(f'<text x="{sx}" y="{sy + 30}" class="label strong">On-Call Ready</text>')
    bx, by = points[current] if current < n else points[-1]
    bob_lift = 62  # Bob stands above his camp
    parts.append(f'<g class="bob" transform="translate({bx - 16},{by - bob_lift})">'
                 '<rect x="4" y="10" width="24" height="20" rx="5"/><rect x="14" y="2" width="4" height="8"/>'
                 '<circle cx="12" cy="20" r="2.5" class="eye"/><circle cx="20" cy="20" r="2.5" class="eye"/>'
                 '<text x="16" y="-4" class="label strong">Bob</text></g>')
    parts.append("</svg>")
    return "".join(parts)


MOUNTAIN_CSS = """
.peak{width:100%;height:auto;display:block;background:var(--panel);border:1px solid var(--line);
border-radius:var(--radius);margin:18px 0}
.peak .m1{fill:color-mix(in srgb,var(--accent2) 22%,var(--panel))}
.peak .m2{fill:color-mix(in srgb,var(--accent) 16%,var(--panel))}
.peak .trail{fill:none;stroke:var(--muted);stroke-width:3;stroke-dasharray:6 7}
.peak .camp{stroke-width:3;stroke:var(--panel)}.peak .camp.cleared{fill:var(--done)}
.peak .camp.here{fill:var(--accent);stroke:var(--gold)}.peak .camp.ahead{fill:var(--lock)}
.peak .flag{fill:var(--gold);stroke:var(--gold);stroke-width:2}
.peak .summit{fill:var(--lock)}.peak .summit.reached{fill:var(--gold)}
.peak .label{font-size:12px;fill:var(--text);text-anchor:middle}.peak .strong{font-weight:700}
.peak .bob rect{fill:var(--accent);stroke:var(--text);stroke-width:1.5}.peak .bob .eye{fill:var(--bg)}
.card h4{padding-right:58px}
.caps{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
padding:14px 18px;margin:0 0 22px}
.caps h3{margin:0 0 8px;font-size:16px}.caps ul{list-style:none;margin:0;padding:0}
.caps li{display:flex;gap:10px;align-items:flex-start;padding:5px 0;border-top:1px solid var(--line);font-size:14px}
.caps li:first-child{border-top:0}
.caps .st{flex:none;width:92px;font-size:12px;font-weight:700;text-transform:uppercase;
letter-spacing:.4px}.caps .on{color:var(--done)}.caps .wip{color:var(--accent)}.caps .off{color:var(--lock)}
.caps li.locked{color:var(--muted)}
"""


def capabilities(zones, cleared, current_part):
    """What Nimbus Store can do now: one real capability per zone, unlocked as the student clears it."""
    rows = []
    for zone in zones:
        if zone["part"] in cleared:
            state, label, cls = "on", "Unlocked", ""
        elif zone["part"] == current_part:
            state, label, cls = "wip", "In progress", ""
        else:
            state, label, cls = "off", "Locked", ' class="locked"'
        rows.append(f'<li{cls}><span class="st {state}">{label}</span><span><strong>{html.escape(zone["name"])}:'
                    f'</strong> {html.escape(zone.get("unlock", ""))}</span></li>')
    return f'<section class="caps"><h3>What Nimbus Store can do now</h3><ul>{"".join(rows)}</ul></section>'


def render(catalog, progress, xp, level, following, next_mission, generated, cleared=()):
    done_ids = set(progress["missions"])
    zones = catalog.get("zones", [])
    climb_level = len(cleared)
    missions = catalog["missions"]
    span = (following["xp"] - level["xp"]) if following else 1
    pct = 100 if not following else int(100 * (xp - level["xp"]) / span)
    to_next = f"{following['xp'] - xp} XP to {html.escape(following['name'])}" if following else "Top level reached"

    if next_mission:
        n = next_mission
        next_html = (f'<section class="next"><div><div class="id">NEXT MISSION · {html.escape(n["id"])} · '
                     f'+{n["xp"]} XP</div><h2>{html.escape(n["title"])}</h2><div>{html.escape(n["goal"])}</div></div>'
                     f'<div>Type to Bob: <code>/next-mission</code></div></section>')
    else:
        next_html = ('<section class="next"><div><h2>Every mission complete!</h2><div>Create your passport.</div></div>'
                     '<div>Type to Bob: <code>/lab-proof Your Name</code></div></section>')

    zones_html = []
    for zone in catalog.get("zones", []):
        zm = [m for m in missions if m["part"] == zone["part"]]
        if not zm:
            continue
        cards = []
        for m in zm:
            unlocked = m["part"] <= (next_mission["part"] if next_mission else 99) or m["id"] in done_ids
            state = "done" if m["id"] in done_ids else ("next" if next_mission and m["id"] == next_mission["id"]
                                                        else ("open" if unlocked else "locked"))
            tag = f'<span class="tag">add-on: {html.escape(m["needs"])}</span>' if m.get("needs") else ""
            reward = f'<span class="tag">badge: {html.escape(m["achievement"])}</span>' if m.get("achievement") else ""
            cards.append(f'<article class="card {state}"><div class="id">{html.escape(m["id"])}</div>'
                         f'<span class="xp">+{m["xp"]} XP</span><h4>{html.escape(m["title"])}</h4>'
                         f'<p>{html.escape(m["goal"])}</p>{tag} {reward}</article>')
        count = sum(1 for m in zm if m["id"] in done_ids)
        zones_html.append(
            f'<div class="zone">{_icon(zone["icon"])}<div><h3>Zone {zone["part"]}: {html.escape(zone["name"])}</h3>'
            f'<p>{html.escape(zone["story"])}</p></div><span class="count">{count}/{len(zm)} done</span></div>'
            f'<div class="grid">{"".join(cards)}</div>')

    badges = "".join(f'<span class="badge{"" if m["id"] in done_ids else " off"}">{_icon("star")}'
                     f'{html.escape(m["achievement"])}</span>' for m in missions if m.get("achievement"))

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SRE Mission Control</title><style>{CSS}{MOUNTAIN_CSS}</style></head>
<body><div class="wrap">
<header><div><h1>SRE <span>Mission Control</span></h1>
<p class="sub">SRE Academy lab · {len(done_ids)}/{len(missions)} missions · updated {html.escape(generated)}</p></div>
<div class="level" style="--pct:{pct}%"><div class="emblem"><div>L{climb_level}</div></div>
<div style="flex:1"><strong>Level {climb_level}/{len(zones)}</strong> · {html.escape(level["name"])} · {xp} XP
<div class="bar"><i style="width:{pct}%"></i></div><div class="sub">{to_next}</div></div></div></header>
<section class="story">{_md_bold(catalog.get("story", ""))} Every zone you clear is a level: help Bob climb all the
way to <strong>On-Call Ready</strong>.</section>
{mountain(zones, set(cleared)) if zones else ""}
{capabilities(zones, set(cleared), next((z["part"] for z in zones if z["part"] not in set(cleared)), None))
 if zones else ""}
{next_html}
{"".join(zones_html)}
<h3 style="margin-top:30px">Achievements</h3><div class="badges">{badges}</div>
<footer>Every mission is verified on your own cluster by <span class="cmd">scripts/lab.py check</span>.
Refresh this page after each mission (Bob does it for you).</footer>
</div></body></html>
"""
