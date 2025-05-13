#!/usr/bin/env python3
import sys
import re

def format_analysis(text: str) -> str:
    """
    Convert a plain-text analysis plan into the desired HTML structure.
    Expects:
      - Text containing a start statement, bullet points prefixed with '- ', and a closing statement.
    """
    # Split into head (start + bullets) and closing based on '---'
    parts = text.split('---', 1)
    head = parts[0].strip()
    closing = parts[1].strip() if len(parts) > 1 else ''

    # Find all numbered bold headings
    section_pattern = re.compile(r"\*\*\s*(\d+)\.\s*(.*?)\*\*")
    matches = list(section_pattern.finditer(head))
    # Extract start statement (everything before the first section heading)
    if matches:
        start = head[:matches[0].start()].strip()
    else:
        start = head
    sections = []
    for i, m in enumerate(matches):
        # Extract heading text
        heading_text = f"{m.group(1)}. {m.group(2)}"
        # Determine the text range for items under this heading
        start_idx = m.end()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(head)
        items_block = head[start_idx:end_idx].strip()
        # Split on ' - ' to get individual items
        items = [itm.strip() for itm in items_block.split(' - ') if itm.strip()]
        # Remove any leading hyphens
        items = [re.sub(r'^-+\s*', '', itm) for itm in items]
        sections.append((heading_text, items))

    # Convert '**bold**' markdown in start and closing only
    bold_pattern = re.compile(r"\*\*(.*?)\*\*")
    start = bold_pattern.sub(r"<b>\1</b>", start)
    closing = bold_pattern.sub(r"<b>\1</b>", closing)

    # Build HTML
    html = []
    html.append('<p class="text-gray-300 text-sm">')
    html.append(f'  {start}')
    html.append('</p>')
    for heading_text, items in sections:
        # Heading line with two breaks before and after
        html.append(f'<br/><b>{heading_text}</b><br/>')
        html.append('<ul class="list-disc list-inside text-gray-300 text-sm space-y-1">')
        for itm in items:
            html.append(f'  <li>{itm}</li>')
        html.append('</ul>')
    html.append('<p class="text-gray-300 text-sm mt-2">')
    html.append(f'  {closing}')
    html.append('</p>')
    return "\n".join(html)


text = """
**Analytický plán pre zmluvu o prenájme nehnuteľnosti (nájomná zmluva):** **1. Identifikácia zmluvných strán** - Overiť úplné identifikačné údaje prenajímateľa a nájomcu (meno, priezvisko, rodné číslo/dátum narodenia, číslo dokladu totožnosti, adresa trvalého pobytu). - Skontrolovať, či sú strany jasne označené ako prenajímateľ a nájomca v celom texte zmluvy. **2. Predmet zmluvy** - Presná špecifikácia prenajímanej nehnuteľnosti (adresa, identifikátor, účel využitia, výmera, vybavenie). - Overiť, či je účel užívania jasne definovaný a či je povolená zmena účelu len s písomným súhlasom prenajímateľa. - Skontrolovať doloženie vlastníckeho práva prenajímateľa (napr. notárska zápisnica). **3. Doba trvania zmluvy** - Určenie doby nájmu (určitá/dobou neurčitá). - Podmienky predĺženia alebo prechodu na neurčitý nájom. - Výpovedná lehota a spôsob jej uplatnenia. **4. Výška nájomného a platobné podmienky** - Výška mesačného nájomného, splatnosť, spôsob platby (bankový prevod, hotovosť). - Povinnosť predloženia dokladu o platbe (príjmový doklad, výpis z účtu). - Dôsledky omeškania s platbou (zmluvné pokuty, možnosť jednostranného ukončenia zmluvy). **5. Zábezpeka (depozit)** - Výška zábezpeky, účel (krytie škôd, nedoplatkov, spotrebných nákladov). - Podmienky vrátenia zábezpeky a jej zúčtovanie. - Možnosť použitia zábezpeky prenajímateľom a povinnosť nájomcu doplniť zábezpeku. - Splatnosť a dôsledky nezloženia zábezpeky. **6. Spotrebné náklady a poplatky** - Určenie, kto hradí spotrebné náklady (energie, voda, internet, TV, údržba spoločných priestorov). - Povinnosť predloženia dokladov o úhrade. - Postup pri úhrade spotrebných nákladov prenajímateľom a refundácia nájomcom. **7. Práva a povinnosti prenajímateľa** - Povinnosť odovzdať nehnuteľnosť v dohodnutom stave a vybavení (vrátane zoznamu zariadenia). - Povinnosť nebrániť užívaniu nehnuteľnosti nájomcom. - Povinnosť vykonávať základné a bežné opravy (ak nie sú spôsobené vinou nájomcu). - Právo na kontrolu stavu nehnuteľnosti (frekvencia, oznámenie vopred). **8. Práva a povinnosti nájomcu** - Povinnosť užívať nehnuteľnosť s náležitou starostlivosťou, udržiavať ju v dobrom stave. - Povinnosť platiť nájomné a spotrebné náklady včas. - Povinnosť dodržiavať domový poriadok, hygienu, bezpečnostné predpisy. - Povinnosť oznámiť škody, poistné udalosti, zásahy tretích osôb. - Povinnosť umožniť prenajímateľovi prístup do nehnuteľnosti (po dohode). - Povinnosť vrátiť nehnuteľnosť v pôvodnom stave (s prihliadnutím na bežné opotrebenie). - Zákaz podnájmu alebo postúpenia užívania tretím osobám bez súhlasu prenajímateľa. - Zákaz vykonávať stavebné úpravy bez písomného súhlasu prenajímateľa a prípadných povolení. **9. Opravy a údržba** - Rozdelenie zodpovednosti za bežné a väčšie opravy (prenajímateľ vs. nájomca). - Postup pri neplnení povinností prenajímateľa (možnosť nájomcu vykonať opravu a započítať náklady, resp. ukončiť zmluvu). **10. Ukončenie zmluvy** - Všetky prípady ukončenia (uplynutie doby, dohoda, výpoveď, porušenie zmluvy). - Výpovedná lehota a forma výpovede (písomne, elektronicky). - Dôsledky predčasného ukončenia (zmluvné pokuty, vrátenie zábezpeky, vyrovnanie záväzkov). **11. Zmluvné pokuty a zodpovednosť** - Výška a podmienky uplatnenia zmluvných pokút (omeškanie s platbou, neoznámenie výpovede, poškodenie nehnuteľnosti, oneskorené vrátenie zábezpeky). - Kumulatívnosť pokút. - Trvanie platnosti pokutových ustanovení aj po ukončení zmluvy. **12. Ochrana osobných údajov a mlčanlivosť** - Povinnosť mlčanlivosti o informáciách získaných počas trvania zmluvy. - Ochrana osobných údajov v súlade s platnou legislatívou. **13. Korešpondencia a doručovanie** - Určenie platných kontaktných adries a e-mailov. - Povinnosť oznámiť zmenu adresy. - Pravidlá pre elektronickú komunikáciu a doručovanie (kedy sa považuje správa za doručenú). **14. Riešenie sporov** - Spôsob riešenia sporov (prednostne dohodou, inak súdne konanie podľa miestnej jurisdikcie). - Určenie rozhodného práva (v tomto prípade bulharské právo). **15. Jazyková verzia a výklad** - Počet vyhotovení a jazykové verzie zmluvy. - Prednosť bulharského textu v prípade rozporu alebo výkladových nejasností. **16. Záverečné a doplňujúce ustanovenia** - Účinnosť zmluvy (dátum podpisu a nadobudnutia platnosti). - Možnosť uzatvárania dodatkov a ich forma. - Ustanovenia o platnosti zmluvy v prípade neplatnosti niektorej časti. **17. Prílohy a súvisiace dokumenty** - Odovzdávací protokol (stav a vybavenie nehnuteľnosti pri odovzdaní). - Zoznam zariadenia a vybavenia. - Prípadné dodatky, dohody, správy. **18. Kontrola súladu s právnymi predpismi** - Súlad s miestnou legislatívou (Obligačný zákon, zákon o ochrane osobných údajov, stavebné predpisy). - Overiť, či zmluva neobsahuje neplatné alebo neprípustné ustanovenia. --- Tento plán slúži ako podrobný kontrolný zoznam pre analýzu nájomných zmlúv na nehnuteľnosti, pričom je potrebné venovať pozornosť každej vyššie uvedenej oblasti a identifikovať prípadné riziká, nejasnosti alebo chýbajúce náležitosti.
"""

def main():
    # Read input from file argument or STDIN
    print(format_analysis(text))


if __name__ == "__main__":
    main()
