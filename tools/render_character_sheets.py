#!/usr/bin/env python3
"""Build portrait character sheets from the canonical campaign Markdown records."""
import base64
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / 'campaigns/silas-venn'
CHARACTERS = CAMPAIGN / 'characters'
SRD = (ROOT / 'dnd-5e-srd/markdown/08 spellcasting.md').read_text()
SKILLS = {'Acrobatics':'DEX','Animal Handling':'WIS','Arcana':'INT','Athletics':'STR',
          'Deception':'CHA','History':'INT','Insight':'WIS','Intimidation':'CHA',
          'Investigation':'INT','Medicine':'WIS','Nature':'INT','Perception':'WIS',
          'Performance':'CHA','Persuasion':'CHA','Religion':'INT','Sleight of Hand':'DEX',
          'Stealth':'DEX','Survival':'WIS'}

def esc(value):
    return html.escape(str(value), quote=True)

def match(pattern, text):
    found = re.search(pattern, text, re.I | re.M)
    if not found:
        raise ValueError(f'Missing sheet field: {pattern}')
    return found

def section(text, title):
    found = re.search(r'^## '+re.escape(title)+r'\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    return found[1].strip() if found else ''

def bullet(text, label):
    return match(r'^- '+re.escape(label)+r': (.+)$', text)[1]

def paragraphs(text):
    return ''.join('<p>'+esc(p)+'</p>' for p in text.split('\n\n') if p.strip())

def items(text):
    return '<ul>'+''.join('<li>'+esc(line[2:])+'</li>' for line in text.splitlines() if line.startswith('- '))+'</ul>'

CSS = '''
:root{--ink:#25362f;--muted:#68736a;--paper:#f4efdf;--line:#d7cfb9;--accent:#366353;--gold:#a77b38}
*{box-sizing:border-box}body{margin:0;background:#172923;color:var(--ink);font-family:Georgia,'Times New Roman',serif;line-height:1.5}a{color:inherit}button{font:inherit;cursor:pointer}.toolbar{max-width:1050px;margin:24px auto;display:flex;justify-content:space-between;gap:14px;align-items:center;color:#e9e4d6;padding:0 18px;font:13px system-ui,sans-serif}.toolbar nav{display:flex;gap:18px;flex-wrap:wrap}.toolbar button{border:1px solid #819586;background:transparent;color:inherit;padding:8px 15px;border-radius:4px}.sheet{max-width:1050px;margin:0 auto 32px;background:var(--paper);box-shadow:0 20px 65px #0005}.page{padding:36px 42px;position:relative}.page+.page{border-top:1px solid var(--line)}.kicker{font:11px system-ui,sans-serif;letter-spacing:2.8px;text-transform:uppercase;color:var(--accent)}.masthead{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid var(--accent);padding-bottom:17px;margin-bottom:24px}.masthead h1{font-size:46px;letter-spacing:-1.5px;line-height:1;margin:10px 0 8px;font-weight:normal}.subtitle{font:13px system-ui,sans-serif;color:var(--muted)}.level{text-align:center;border:1px solid var(--line);padding:9px 18px}.level strong{display:block;font-size:28px;line-height:1.1}.level span{font:10px system-ui,sans-serif;letter-spacing:1px}.hero{display:grid;grid-template-columns:35% 1fr;gap:26px}.portrait{margin:0;position:relative;background:#26392f}.portrait img{width:100%;height:auto;display:block}.portrait figcaption{padding:10px 14px;background:var(--accent);color:#f5efdf;font:11px system-ui,sans-serif;letter-spacing:1px}.status{display:flex;flex-direction:column;gap:16px}.vitals{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.tile{padding:12px 10px;border:1px solid var(--line);text-align:center;background:#fff4}.tile .value{font-size:30px;line-height:1.2}.label{font:10px system-ui,sans-serif;letter-spacing:1px;text-transform:uppercase;color:var(--muted)}.health{padding:16px 18px;background:var(--accent);color:#fff8e8}.health .label{color:#dce5d8}.health strong{font-size:38px;font-weight:normal}.health small{font:12px system-ui,sans-serif}.bar{height:5px;background:#ffffff40;margin-top:9px}.bar span{display:block;height:100%;background:#dce5ac}.abilities{display:grid;grid-template-columns:repeat(6,1fr);gap:7px}.ability{border:1px solid var(--line);text-align:center;padding:8px 2px}.ability strong{font-size:23px;display:block;line-height:1.2}.ability small{font:12px system-ui,sans-serif}.resource{border-top:1px solid var(--line);padding-top:12px}.resource-line{display:flex;justify-content:space-between;gap:15px;font:13px system-ui,sans-serif;margin-bottom:8px}.pips{display:inline-flex;gap:5px;vertical-align:middle;margin-left:8px}.pip{width:12px;height:12px;border:1px solid var(--accent);border-radius:50%}.pip.available{background:var(--accent)}.concentration{font:12px system-ui,sans-serif;padding:10px 12px;background:#e3e9da;border-left:3px solid var(--accent)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:24px}.panel h2,.page>h2{font-weight:normal;font-size:22px;margin:0 0 12px;padding-bottom:5px;border-bottom:1px solid var(--line)}.skill-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 18px}.row{display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:4px 0;font:12px system-ui,sans-serif}.row .number{font-family:ui-monospace,monospace;font-weight:600}.trained:before{content:'●';font-size:8px;color:var(--accent);margin-right:6px}.untrained:before{content:'○';font-size:8px;color:var(--muted);margin-right:6px}.save-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px 12px}.tiny{font:11px system-ui,sans-serif;color:var(--muted)}.panel p,.panel li{font-size:13px}.panel ul{padding-left:18px;margin:8px 0}.attacks .row{border-bottom:1px solid var(--line);align-items:flex-start}.attack-note{max-width:85%;font-size:12px}.passives{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px}.passives strong{font:18px Georgia,serif}.footer{display:flex;justify-content:space-between;gap:15px;border-top:1px solid var(--line);margin-top:24px;padding-top:12px;font:10px system-ui,sans-serif;color:var(--muted);letter-spacing:.5px}.spell-group{margin:18px 0}.spell-group h3{font:11px system-ui,sans-serif;text-transform:uppercase;letter-spacing:1.5px;color:var(--accent)}.spells{display:grid;grid-template-columns:1fr 1fr;gap:10px}.spell{border:1px solid var(--line);background:#ffffff30;padding:10px 12px}.spell summary{cursor:pointer;font-size:16px}.spell .meta{font:10px system-ui,sans-serif;color:var(--muted);margin-top:5px;line-height:1.6}.spell .description{font-size:12px;margin-top:10px;white-space:pre-line}.tag{display:inline-block;margin-left:5px;border:1px solid #b8c5ac;padding:0 4px;font:9px system-ui,sans-serif;text-transform:uppercase;vertical-align:middle}.story{font-size:13px}.milestone{margin-top:22px;padding:15px 18px;border:1px solid var(--line);background:#e9e5d6}.milestone p{font-size:12px;margin:6px 0}.milestone h3{font-weight:normal;margin:0;font-size:18px}.mara{--accent:#766038;--ink:#37382b}.mara .concentration{background:#eae5d5}.mara .portrait{background:#473d27}
@media(max-width:760px){.page{padding:22px}.masthead h1{font-size:36px}.hero{grid-template-columns:1fr}.portrait{max-width:440px;margin:auto}.grid{grid-template-columns:1fr}.abilities{gap:5px}.spells{grid-template-columns:1fr}.toolbar{margin:14px auto}.masthead{gap:10px}.level{padding:8px 12px}}
@media print{@page{size:A4;margin:11mm}body{background:white;color:#223027;print-color-adjust:exact;-webkit-print-color-adjust:exact}.toolbar{display:none}.sheet{margin:0;box-shadow:none;max-width:none}.page{padding:0;break-after:page}.page:last-child{break-after:auto}.page+.page{border:0;padding-top:0}.masthead{margin-bottom:4mm;padding-bottom:3mm}.masthead h1{font-size:28pt}.hero{grid-template-columns:34% 1fr;gap:6mm}.portrait img{max-height:118mm;object-fit:cover}.status{gap:3mm}.vitals{gap:2mm}.tile{padding:2mm}.tile .value{font-size:20pt}.health{padding:3mm}.health strong{font-size:25pt}.abilities{gap:1.5mm}.ability{padding:1.5mm}.ability strong{font-size:16pt}.grid{margin-top:5mm;gap:6mm}.row{font-size:8pt;padding:1mm 0}.panel h2{font-size:14pt;margin-bottom:2mm}.panel p,.panel li,.story{font-size:8pt}.spell{padding:2mm;break-inside:avoid}.spell summary{font-size:10pt}.spell .meta{font-size:7pt}.spells{gap:2mm}.spell-group{margin:3mm 0}.footer{margin-top:4mm;padding-top:2mm;font-size:7pt}.milestone{margin-top:4mm;padding:3mm}.spell:not([open]) .description{display:none}}
'''

def spell_card(name):
    found = re.search(r'^#### '+re.escape(name)+r'\n(.*?)(?=^#### |\Z)', SRD, re.M | re.S | re.I)
    if not found:
        return '<details class="spell"><summary>'+esc(name)+'<span class="tag">ritual</span></summary><div class="meta">1st-level conjuration · 1 hour · 10 feet · Instantaneous</div><div class="description">Summon a familiar. Requires 10 gp of consumed charcoal, incense, and herbs in a brass brazier. No familiar is currently summoned; these materials and brazier are not owned.</div></details>' if name == 'Find Familiar' else (_ for _ in ()).throw(ValueError('Spell absent from local SRD: '+name))
    body = found[1].strip()
    school = body.splitlines()[0].strip('*')
    fields = dict(re.findall(r'\*\*(Casting Time|Range|Components|Duration):\*\* ([^\n]+)', body))
    tags = ('<span class="tag">ritual</span>' if '(ritual)' in school else '')
    if 'Concentration' in fields.get('Duration',''):
        tags += '<span class="tag">concentration</span>'
    meta = esc(school.replace(' (ritual)',''))+'<br>'+esc(fields['Casting Time']+' · '+fields['Range']+' · '+fields['Duration'])
    description = re.sub(r'\*\*([^*]+)\*\*', r'\1', body)
    description = re.sub(r'(?<!\*)\*([^*]+)\*',r'\1',description)
    return f'<details class="spell"><summary>{esc(name)}{tags}</summary><div class="meta">{meta}</div><div class="description">{esc(description)}</div></details>'

def render(slug):
    text = (CHARACTERS / (slug+'.md')).read_text()
    name = text.splitlines()[0][2:]
    wizard = slug == 'silas-venn'
    identity = section(text,'Basic information' if wizard else 'Identity')
    combat = section(text,'Combat and resources')
    spells = section(text,'Spellcasting')
    gear = section(text,'Proficiencies and equipment' if wizard else 'Equipment and money')
    klass = 'Wizard' if wizard else 'Druid'
    level = int(match(r'\b'+klass+r' (\d+)', identity)[1])
    age = match(r'age (\d+)',identity)[1]
    background = bullet(identity,'Background' if wizard else 'Custom background').split(',')[0].split('.')[0]
    hp, maximum = map(int,match(r'^- HP: (\d+)/(\d+)',combat).groups())
    ac = match(r'^- AC: (\d+)',combat)[1]
    pb = int(match(r'proficiency bonus:? \+(\d+)',combat)[1])
    slots, total = map(int,match(r'(?:Spell slots:|Level 1 slots:) (\d+)/(\d+)',spells).groups())
    gold = match(r'(?:^- Gold: |remaining gold: )(\d+) gp',gear)[1]
    initiative = match(r'Initiative: ([+-]\d+)',combat)[1]
    speed = match(r'Speed: (\d+)',combat)[1]
    hit_dice = match(r'Hit Dice: ([^.;\n]+)',combat)[1]
    concentration = bullet(spells,'Concentration').split('. ')[0]
    condition = match(r'Conditions: ([^.;\n]+)',combat)[1]
    abilities = {}
    for line in text.splitlines():
        if re.match(r'^\| (STR|DEX|CON|INT|WIS|CHA) ',line):
            parts = [p.strip() for p in line.strip('|').split('|')]
            score = int(parts[-2])
            abilities[parts[0]] = (score,(score-10)//2)
    if len(abilities) != 6 or hp > maximum or slots > total:
        raise ValueError('Invalid abilities or current resources in '+slug)
    ability_html = ''.join(f'<div class="ability"><div class="label">{a}</div><strong>{v[0]}</strong><small>{v[1]:+d}</small></div>' for a,v in abilities.items())
    skill_html = ''
    for skill, ability in SKILLS.items():
        trained = re.search(r'\b'+re.escape(skill)+r' \+(-?\d+)',text)
        bonus = int(trained[1]) if trained else abilities[ability][1]
        skill_html += f'<div class="row"><span class="{"trained" if trained else "untrained"}">{esc(skill)}</span><span class="number">{bonus:+d}</span></div>'
    save_html = ''.join(f'<div class="row"><span class="{"trained" if a in ("INT","WIS") else "untrained"}">{a}</span><span class="number">{m+ (pb if a in ("INT","WIS") else 0):+d}</span></div>' for a,(s,m) in abilities.items())
    dc = match(r'(?:Spell save DC|spell save DC):? (\d+)',spells)[1]
    attack = match(r'(?:spell attack bonus|spell attack):? ([+-]\d+)',spells)[1]
    cantrips = bullet(spells,'Cantrips').split('. ')[0].rstrip('.').split(', ')
    # The sentence after Mara's cantrip list describes Guidance, not another spell.
    cantrips = [n for c in cantrips for n in c.split('.')[0].split(' and ')]
    prepared = bullet(spells,"Starting spellbook and today's prepared spells" if wizard else 'Prepared spells').rstrip('.').split(', ')
    all_spell_cards = '<div class="spell-group"><h3>Cantrips · at will</h3><div class="spells">'+''.join(spell_card(n) for n in cantrips)+'</div></div>'
    all_spell_cards += '<div class="spell-group"><h3>Prepared level 1 spells · '+str(len(prepared))+' prepared</h3><div class="spells">'+''.join(spell_card(n) for n in prepared)+'</div></div>'
    portrait = base64.b64encode((CHARACTERS/'portraits'/f'{slug}.png').read_bytes()).decode()
    pips = ''.join('<span class="pip'+(' available' if n < slots else '')+'"></span>' for n in range(total))
    saves = '<div class="save-grid">'+save_html+'</div>'
    weapons = [line[2:] for line in text.splitlines() if re.match(r'^- (Dagger|Quarterstaff|Produce Flame):',line)]
    attacks = ''.join('<div class="row"><span class="attack-note">'+esc(w)+'</span></div>' for w in weapons)
    languages = bullet(section(text,'Proficiencies and equipment') if wizard else section(text,'Combat and resources'),'Languages')
    tools = bullet(section(text,'Proficiencies and equipment') if wizard else section(text,'Combat and resources'),'Tools')
    features = [line[2:] for line in spells.splitlines() if line.startswith('- ') and any(k in line for k in ['Arcane Recovery:','A familiar','Early necromancy','Druid ritual','No Wild Shape','Healing Word:'])]
    features.append('Tradition at level 2: School of Necromancy.' if wizard else 'Druid circle at level 2: Circle of the Land (forest).')
    death = match(r'Death saves: ([^.\n]+)',combat)[1]
    footer = '<div class="footer"><span>The Glass Road · D&D 5e / 2014</span><span>Session 1 · 6 Harvest, 812</span></div>'
    concept = 'Apothecary apprentice · Student of necromancy' if wizard else 'Medicinal field researcher · Field naturalist'
    story = section(text,'Backstory') if wizard else '\n\n'.join(line[2:] for line in identity.splitlines() if line.startswith(('- Goal:','- Personality:','- She evaluates')))
    inventory = '\n'.join(line for line in gear.splitlines() if line.startswith('- ') and any(k in line for k in ['Class equipment:','Explorer','Background equipment:','Gold:','No owned','No potions','At creation','money is tracked']))
    milestone = json.loads((CAMPAIGN/'milestones.json').read_text())['active'][0]
    milestone_html = '<div class="milestone"><div class="kicker">Next milestone · '+esc(milestone['id'])+'</div><h3>Level '+str(milestone['resulting_level'])+'</h3><p>'+esc(milestone['criterion'])+'</p><p>Status: active · no advancement awarded</p></div>'
    return f'''<article class="sheet {'silas' if wizard else 'mara'}" id="{slug}">
<section class="page"><header class="masthead"><div><div class="kicker">The Glass Road / Character record</div><h1>{esc(name)}</h1><div class="subtitle">Human · {klass} {level} · Age {age} · {esc(background)}</div></div><div class="level"><span>LEVEL</span><strong>{level}</strong></div></header>
<div class="hero"><figure class="portrait"><img src="data:image/png;base64,{portrait}" alt="Portrait of {esc(name)}" width="1024" height="1536"><figcaption>{esc(concept)}</figcaption></figure><div class="status">
<div class="health"><div class="label">Hit points</div><strong>{hp}</strong> <small>/ {maximum} maximum · temporary HP 0</small><div class="bar"><span style="width:{100*hp/maximum:.1f}%"></span></div></div>
<div class="vitals">{''.join(f'<div class="tile"><div class="label">{label}</div><div class="value">{esc(value)}</div></div>' for label,value in [('Armor class',ac),('Initiative',initiative),('Speed',speed+' ft'),('Proficiency',f'+{pb}'),('Spell save DC',dc),('Spell attack',attack)])}</div>
<div class="abilities">{ability_html}</div><div class="resource"><div class="resource-line"><span>Level 1 spell slots <span class="pips">{pips}</span></span><strong>{slots} / {total} available</strong></div><div class="resource-line"><span>Hit Dice</span><strong>{esc(hit_dice)}</strong></div><div class="resource-line"><span>Gold</span><strong>{gold} gp</strong></div><div class="resource-line"><span>Conditions</span><strong>{esc(condition)}</strong></div><div class="tiny">Death saves: {esc(death)}</div></div><div class="concentration"><strong>Concentration:</strong> {esc(concentration)}</div></div></div>
<div class="grid"><section class="panel"><h2>Skills</h2><div class="skill-grid">{skill_html}</div><div class="tiny">● Proficient · ○ Untrained</div></section><section class="panel"><h2>Saving throws</h2>{saves}<h2 style="margin-top:18px">Attacks</h2><div class="attacks">{attacks}</div><div class="passives"><span class="tiny">Passive Perception <strong>{abilities['WIS'][1]+10+(pb if re.search(r'Perception \+',text) else 0)}</strong></span><span class="tiny">Passive Investigation <strong>{abilities['INT'][1]+10+pb}</strong></span></div></section></div>{footer}</section>
<section class="page"><div class="kicker">{esc(name)} / Spellcasting & field notes</div><h2 style="margin-top:10px">Spellbook & prepared magic</h2><div class="tiny">{'Intelligence' if wizard else 'Wisdom'} casting · Save DC {dc} · Attack {attack} · {slots}/{total} level 1 slots available · Expand a spell for its rules.</div>{all_spell_cards}
<div class="grid"><section class="panel"><h2>Features & training</h2><ul>{''.join('<li>'+esc(f)+'</li>' for f in features)}</ul><p><strong>Tools:</strong> {esc(tools)}</p><p><strong>Languages:</strong> {esc(languages)}</p></section><section class="panel"><h2>Equipment & supplies</h2>{items(inventory)}</section></div>
<div class="story"><h2 style="font-size:22px;font-weight:normal;border-bottom:1px solid var(--line);margin-bottom:10px">Ambition & history</h2>{paragraphs(story)}</div>{milestone_html}{footer}</section></article>'''

def document(title, content):
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' · The Glass Road</title><style>'+CSS+'</style></head><body><div class="toolbar"><nav><a href="silas-venn.html">Silas Venn</a><a href="mara-kest.html">Mara Kest</a><a href="party-sheets.html">Both sheets</a></nav><button type="button" onclick="window.print()">Print / Save PDF</button></div>'+content+'</body></html>'

def main():
    rendered = {}
    for slug in ['silas-venn','mara-kest']:
        rendered[slug] = render(slug)
        (CHARACTERS/(slug+'.html')).write_text(document(slug.replace('-',' ').title(),rendered[slug]))
    (CHARACTERS/'party-sheets.html').write_text(document('Party character sheets',''.join(rendered.values())))
    print('Rendered Silas, Mara, and combined printable sheets from current Markdown records.')

if __name__ == '__main__':
    main()
