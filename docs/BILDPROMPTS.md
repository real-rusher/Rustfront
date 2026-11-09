# Bild-Prompts fuer Waffen und Gegenstaende (Menue)

Jeder Block unten ist ein **fertiger Prompt**: komplett kopieren und so in
den Bildgenerator einfuegen - nichts zusammensetzen. Stil, Blickwinkel und
was vermieden werden soll, stehen in jedem Prompt schon drin, damit alle
Bilder zusammenpassen.

Format: **16:9** einstellen (z. B. 1536 x 864). Bei Midjourney steht
`--ar 16:9 --style raw` schon am Ende jedes Prompts; bei anderen
Generatoren diese letzten Zeichen einfach mitkopieren schadet nicht, oder
weglassen.

Dateiname zum Speichern: die Kennung in Klammern, z. B. `sturm.png`.

**Eingebaut seit 0.34.82:** Die Bilder liegen als `assets/menue/<kennung>.jpg`
(640 breit) und erscheinen im Menue AUSRUESTUNG. Seit 0.34.83 sind alle 57
da (Stacheldraht, Horchposten und Raketenbuendel nachgereicht). Ein Bild
ersetzen: als `assets/menue/<kennung>.jpg` (oder .png)
ablegen, fertig.

## Schusswaffen

### REPETIERER (`repetierer.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A long bolt-action rifle with a weathered wooden stock wrapped in cloth tape, a sturdy bolt handle, iron sights and a leather sling with brass buckles, sand-scoured barrel. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### STURMGEWEHR (`sturm.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A rugged assault rifle assembled from mismatched parts, a curved 30-round magazine, a short red-dot sight held on with hose clamps, a folding stock with a padded cheek rest, faded olive paint. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SCHARFSCHÜTZE (`scharf.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A long precision sniper rifle with a large scope wrapped in sun-bleached canvas, a bipod folded under the barrel, a sand-colored ghillie strip along the stock, a heavy muzzle brake. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### MG (`lmg.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A heavy light machine gun with a box magazine full of linked brass cartridges, a carrying handle, a deployed bipod and a perforated barrel shroud blackened by heat. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SCHROT (`schrot.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A pump-action shotgun with a scuffed wooden pump, a row of red shells strapped to the stock with elastic bands, a short barrel and a dented heat shield. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### REVOLVER (`revolver.png`)

Seit 0.34.96 neu gefasst (der alte Prompt lieferte mehrere Teile und lose
Patronen statt eines klaren Revolvers):

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: exactly one heavy six-shot revolver, complete and fully visible, long octagonal barrel with a blade front sight, a fluted cylinder with six visible chambers and a worn engraved band, an exposed hammer and trigger guard, a curved grip wrapped tightly in sun-faded cord with a brass lanyard ring at the bottom, gunmetal frame with rust in the seams and bare steel worn shiny at the edges. The revolver lies alone, nothing next to it. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, loose bullets, cartridges, holster, second gun, open cylinder, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### ZWILLINGE (`zwillinge.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A matched pair of compact pistols lying crossed, one painted amber and one teal, with worn grips and extended magazines. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### MASCHINENPISTOLE (`mp.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A compact submachine gun with a long stick magazine, a wire folding stock, a short suppressor wrapped in tape and a vertical foregrip. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### PRÄZISIONSGEWEHR (`praezision.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A semi-automatic marksman rifle with a slim fluted barrel, an adjustable skeleton stock, a mid-size scope with flip-up covers and a small box magazine. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### UNTERHEBELGEWEHR (`unterhebel.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A lever-action rifle with a large loop lever, brass receiver gone dull with dust, a saddle-ring and a leather wrap on the forend. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### PANZERBÜCHSE (`panzerbuechse.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A massive anti-armor rifle almost as long as a man, a huge rectangular muzzle brake, a padded shoulder plate, a monopod and a single oversized cartridge beside it. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### DOPPELFLINTE (`doppelflinte.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A sawn-off double-barrel shotgun with side-by-side barrels, exposed hammers, a short pistol grip and two spent red shells next to it. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### AUTOSCHROT (`autoschrot.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A bulky automatic shotgun with a drum magazine, a boxy receiver with welded reinforcement plates and a short ventilated barrel. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### MINIGUN (`minigun.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A rotary six-barrel gatling gun with a motor housing, a long belt of ammunition feeding from a backpack-style box, carry handles and heat-darkened barrel tips. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### BOLZENSCHUSSGERÄT (`bolzer.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: An industrial captive-bolt gun repurposed as a close-range weapon: a heavy steel cylinder with a trigger grip, warning stripes in faded yellow and black, a pressure hose. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### NAGLER (`nagler.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A construction nail gun converted into a weapon, a long magazine of nails, a compressed-air canister strapped on top, bright safety orange paint worn down to metal. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SPIEGELLASER (`spiegellaser.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: An improvised laser rifle built around a polished mirror tube and a glass focusing lens, cables running to a battery pack, a faint red glow inside the barrel. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

## Werfer und Raketen

### GRANATWERFER (`granatwerfer.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A six-shot revolver-cylinder grenade launcher with a fat rotating drum, a folding stock, a ladder sight and stubby 40mm grenades with brass bases next to it. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### RAKETENWERFER (`rakete.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A shoulder-fired rocket launcher tube with a pointed warhead loaded at the front, an optical sight with a rubber eyecup, a carrying strap and stenciled warning marks without letters. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### EINWEG-RAKETENWERFER (`einwegwerfer.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A compact disposable rocket tube in faded olive with flip-up sights and pull tabs, extended and ready, scuffed end caps hanging from a cord. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### RAKETENBÜNDEL (`raketenbuendel.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A cluster of four short rocket tubes strapped together with steel bands and a shared pistol grip, small fin-stabilized rockets visible in the openings. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

## Strahl, Blitz und Feuer

### SPULENGEWEHR (`spule.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A coilgun rifle with a row of copper electromagnetic coils along the barrel, exposed capacitors, glowing teal charge indicators and a heavy battery in the stock. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### KETTENBLITZ (`kettenblitz.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A lightning projector with two prongs at the muzzle, a glass chamber filled with a crackling electric arc, insulated cables and ceramic insulators, faint blue sparks. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### KUGELBLITZ (`kugelblitz.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A stubby launcher whose open chamber holds a floating ball of white-blue plasma held between three metal claws, cooling fins along the body. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### FLAMMENWERFER (`flammenwerfer.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A flamethrower wand with a small pilot flame at the nozzle, a hose leading to a twin-tank backpack painted rust red, heat-scorched metal and pressure gauges. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

## Nahkampf

### BRECHEISEN (`brecheisen.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A heavy steel crowbar with a curved claw, chipped red paint, a grip wrapped in leather strips, dents from many blows. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### VORSCHLAGHAMMER (`hammer.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A sledgehammer with a massive square steel head, a long wooden handle wrapped near the end, spikes welded to one face. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SCHOCKSTAB (`schockstab.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A stun baton with two electrodes at the tip arcing with a small blue spark, a rubber grip and a battery housing with a teal indicator light. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SCHLAGRING (`schlagring.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A pair of heavy brass knuckles with worn studs, lying on a strip of cloth tape. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### KETTENSÄGE (`kettensaege.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A compact chainsaw with a scratched engine housing, a long guide bar with sharp chain teeth, a pull cord and fuel stains. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### WURFMESSER (`wurfmesser.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A fan of three balanced throwing knives with cord-wrapped handles, arranged in a leather holster. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SPEER (`speer.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A scavenged spear: a sharpened steel blade lashed to a long pole with wire and cloth, feathers and a small charm tied below the blade. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

## Wurfwaffen und Sprengstoff

### GRANATE (`granate.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A classic fragmentation hand grenade with a segmented olive body, a spoon lever and a pull ring, a little dust on the top. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### RAUCHGRANATE (`rauch.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A cylindrical smoke grenade with a gray canister, a ring pull and a thin wisp of white smoke escaping from the top. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### BLENDGRANATE (`blend.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A stun grenade with a perforated cylindrical body, bright white bands, a ring pull and a faint flash of light inside the holes. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### MOLOTOW (`molotov.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A glass bottle filled with amber fuel, a burning cloth rag stuffed in the neck, soot on the glass. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### C4 (`c4.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A block of plastic explosive wrapped in olive film, a detonator with two wires and a blinking red light, a small remote trigger beside it. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### HAFTLADUNG (`haftladung.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A round sticky charge with a magnetic base and a glue rim, a timer dial on top and an amber indicator light. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### EMP-GRANATE (`emp.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A grenade with a copper-wound core visible through a cage, a teal glow inside and small arcs of electricity. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### GASGRANATE (`gas.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A canister grenade with yellow-green hazard bands, a valve on top leaking a thin greenish vapor. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### KULLER (`kuller.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A heavy round grenade shaped like a bowling ball with grip grooves and a recessed fuse, meant to be rolled. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### KNALLER (`knaller.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A bundle of three firecracker-like charges tied together with string, a single fuse sparkling at the end. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SCHNEEBALL (`schneeball.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A perfectly packed snowball with frost crystals, lying on a small piece of dark cloth, a cold blue light on it (a joke weapon). Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

## Gegenstaende und Ausruestung

### MEDKIT (`medkit.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A rugged first-aid kit: a dented metal case with a faded cross shape, open, showing bandages, a syringe and a small bottle. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### MUNITIONSKISTE (`munikiste.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: An ammunition crate with a hinged lid, rope handles, stenciled stripes, brass cartridges spilling out. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### RAKETENKISTE (`rpg_kiste.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A long wooden crate with a single rocket resting in foam padding, lid leaning against the side. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SANITASCHE (`sanitasche.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A medic satchel with a strap, a cross-shaped patch, pockets bulging with bandages and a tourniquet hanging out. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### MUNITIONSKISTE (STEHT) (`munitionskiste.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A deployable ammo station: a tall metal box on short legs with open drawers of magazines and shells. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SELBSTSCHUSSANLAGE (`geschuetz.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A small automated sentry gun on a tripod, a boxy turret with a camera eye, an ammo belt and a teal status light. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### HORCHPOSTEN (`horchposten.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A listening post: a tripod with a parabolic microphone dish, headphones hanging from it, a small antenna. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SPÄHDROHNE (`drohne.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A small four-rotor scout drone with a camera gimbal, scratched propellers and a blinking amber light. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SPRENGFALLE (`sprengfalle.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A pressure-plate landmine half buried in sand, with a thin tripwire variant beside it and a small warning flag. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SANDSACKWAND (`sandsackwand.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A short wall of stacked burlap sandbags, some torn and leaking sand, a few bullet holes. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### STACHELDRAHT (`stacheldraht.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A coil of razor wire on wooden stakes, catching the light, a strip of torn cloth caught on a barb. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### BENZINKANISTER (`kanister.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A red jerrycan full of fuel, dented and scratched, a spout attached, a drop of fuel on the cap. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### KRÄHENFÜSSE (`kraehenfuesse.png`)

```
Dustfront weapon showcase, a single set of items centered as one display, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A handful of steel caltrops scattered on sand, each with four sharp points, one in focus in the foreground. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```

### SCHILD (`schild.png`)

```
Dustfront weapon showcase, a single item centered, side view facing right, slight three-quarter angle, displayed like a museum piece on a dark matte background with a soft warm rim light from the upper left and a subtle orange glow from below, dusty post-apocalyptic desert-war setting, hand-built scavenged military hardware, worn paint, sand in the seams, scratched metal, cloth tape and leather wraps, muted khaki, rust and gunmetal palette with small amber and teal accents, highly detailed semi-realistic digital painting, crisp silhouette, no hands, no people, no text, no logos. Item: A tall riot shield made from scavenged steel plates riveted together, a narrow view slot, dents from many bullets. Avoid: text, letters, numbers, watermark, logo, brand names, signature, hands, people, more than one item, cropped item, blur, cartoon or toy look, plastic, chrome showroom look, and any real existing firearm model. --ar 16:9 --style raw
```
