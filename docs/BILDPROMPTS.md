# Bild-Prompts fuer Waffen und Gegenstaende (Menue)

Gewuenscht (0.34.80): "Prompts fuer jede Waffe oder jedes Item, die ich einem
Bildgenerator gebe, damit die Waffen im Menue cooler und anders als im Spiel
selbst aussehen."

Im Spiel sind die Waffen kleine Pixelbilder von oben. Fuer das Menue sollen
es grosse, detaillierte Seitenansichten sein - wie Ausstellungsstuecke. Damit
alle Bilder zusammenpassen, beginnt **jeder** Prompt mit demselben Stilblock.

## So benutzen

1. Den **Stilblock** kopieren, direkt dahinter den Prompt der Waffe.
2. Den **Negativ-Prompt** ins Feld "negative prompt" (wo es das gibt; sonst
   weglassen).
3. Format: **16:9** (z. B. 1536 x 864). Bei Midjourney `--ar 16:9 --style raw`
   anhaengen.
4. Gleiche Einstellungen fuer alle Bilder behalten (Modell, Seed-Verhalten,
   Stil-Staerke) - sonst sieht jede Waffe aus wie aus einem anderen Spiel.
5. Dateiname: die Kennung aus der Tabelle, also z. B. `sturm.png`. Wer will,
   legt sie spaeter unter `assets/menue/` ab; eingebaut sind sie noch nicht
   (das Menue AUSRUESTUNG zeigt bisher das Pixelbild aus dem Spiel).

## Stilblock (vor jeden Prompt)

```
Dustfront weapon showcase, a single item centered, side view facing right,
slight three-quarter angle, displayed like a museum piece on a dark matte
background with a soft warm rim light from the upper left and a subtle orange
glow from below, dusty post-apocalyptic desert-war setting, hand-built
scavenged military hardware, worn paint, sand in the seams, scratched metal,
cloth tape and leather wraps, muted khaki, rust and gunmetal palette with
small amber and teal accents, highly detailed semi-realistic digital painting,
crisp silhouette, no hands, no people, no text, no logos.
```

## Negativ-Prompt

```
text, letters, watermark, logo, brand name, signature, hands, person,
multiple items, cropped item, blurry, low detail, cartoon, toy, plastic,
chrome showroom look, futuristic sci-fi neon (unless asked), photo of a real
existing firearm model
```

## Schusswaffen

| Kennung | Name im Spiel | Prompt (nach dem Stilblock) |
| --- | --- | --- |
| `repetierer` | REPETIERER | A long bolt-action rifle with a weathered wooden stock wrapped in cloth tape, a sturdy bolt handle, iron sights and a leather sling with brass buckles, sand-scoured barrel. |
| `sturm` | STURMGEWEHR | A rugged assault rifle assembled from mismatched parts, a curved 30-round magazine, a short red-dot sight held on with hose clamps, a folding stock with a padded cheek rest, faded olive paint. |
| `scharf` | SCHARFSCHÜTZE | A long precision sniper rifle with a large scope wrapped in sun-bleached canvas, a bipod folded under the barrel, a sand-colored ghillie strip along the stock, a heavy muzzle brake. |
| `lmg` | MG | A heavy light machine gun with a box magazine full of linked brass cartridges, a carrying handle, a deployed bipod and a perforated barrel shroud blackened by heat. |
| `schrot` | SCHROT | A pump-action shotgun with a scuffed wooden pump, a row of red shells strapped to the stock with elastic bands, a short barrel and a dented heat shield. |
| `revolver` | REVOLVER | A heavy six-shot revolver with a long barrel, an engraved but worn cylinder, a grip wrapped in cord, a few loose brass rounds lying beside it. |
| `zwillinge` | ZWILLINGE | A matched pair of compact pistols lying crossed, one painted amber and one teal, with worn grips and extended magazines. |
| `mp` | MASCHINENPISTOLE | A compact submachine gun with a long stick magazine, a wire folding stock, a short suppressor wrapped in tape and a vertical foregrip. |
| `praezision` | PRÄZISIONSGEWEHR | A semi-automatic marksman rifle with a slim fluted barrel, an adjustable skeleton stock, a mid-size scope with flip-up covers and a small box magazine. |
| `unterhebel` | UNTERHEBELGEWEHR | A lever-action rifle with a large loop lever, brass receiver gone dull with dust, a saddle-ring and a leather wrap on the forend. |
| `panzerbuechse` | PANZERBÜCHSE | A massive anti-armor rifle almost as long as a man, a huge rectangular muzzle brake, a padded shoulder plate, a monopod and a single oversized cartridge beside it. |
| `doppelflinte` | DOPPELFLINTE | A sawn-off double-barrel shotgun with side-by-side barrels, exposed hammers, a short pistol grip and two spent red shells next to it. |
| `autoschrot` | AUTOSCHROT | A bulky automatic shotgun with a drum magazine, a boxy receiver with welded reinforcement plates and a short ventilated barrel. |
| `minigun` | MINIGUN | A rotary six-barrel gatling gun with a motor housing, a long belt of ammunition feeding from a backpack-style box, carry handles and heat-darkened barrel tips. |
| `bolzer` | BOLZENSCHUSSGERÄT | An industrial captive-bolt gun repurposed as a close-range weapon: a heavy steel cylinder with a trigger grip, warning stripes in faded yellow and black, a pressure hose. |
| `nagler` | NAGLER | A construction nail gun converted into a weapon, a long magazine of nails, a compressed-air canister strapped on top, bright safety orange paint worn down to metal. |
| `spiegellaser` | SPIEGELLASER | An improvised laser rifle built around a polished mirror tube and a glass focusing lens, cables running to a battery pack, a faint red glow inside the barrel. |

## Werfer und Raketen

| Kennung | Name im Spiel | Prompt (nach dem Stilblock) |
| --- | --- | --- |
| `granatwerfer` | GRANATWERFER | A six-shot revolver-cylinder grenade launcher with a fat rotating drum, a folding stock, a ladder sight and stubby 40mm grenades with brass bases next to it. |
| `rakete` | RAKETENWERFER | A shoulder-fired rocket launcher tube with a pointed warhead loaded at the front, an optical sight with a rubber eyecup, a carrying strap and stenciled warning marks without letters. |
| `einwegwerfer` | EINWEG-RAKETENWERFER | A compact disposable rocket tube in faded olive with flip-up sights and pull tabs, extended and ready, scuffed end caps hanging from a cord. |
| `raketenbuendel` | RAKETENBÜNDEL | A cluster of four short rocket tubes strapped together with steel bands and a shared pistol grip, small fin-stabilized rockets visible in the openings. |

## Strahl, Blitz und Feuer

| Kennung | Name im Spiel | Prompt (nach dem Stilblock) |
| --- | --- | --- |
| `spule` | SPULENGEWEHR | A coilgun rifle with a row of copper electromagnetic coils along the barrel, exposed capacitors, glowing teal charge indicators and a heavy battery in the stock. |
| `kettenblitz` | KETTENBLITZ | A lightning projector with two prongs at the muzzle, a glass chamber filled with a crackling electric arc, insulated cables and ceramic insulators, faint blue sparks. |
| `kugelblitz` | KUGELBLITZ | A stubby launcher whose open chamber holds a floating ball of white-blue plasma held between three metal claws, cooling fins along the body. |
| `flammenwerfer` | FLAMMENWERFER | A flamethrower wand with a small pilot flame at the nozzle, a hose leading to a twin-tank backpack painted rust red, heat-scorched metal and pressure gauges. |

## Nahkampf

| Kennung | Name im Spiel | Prompt (nach dem Stilblock) |
| --- | --- | --- |
| `brecheisen` | BRECHEISEN | A heavy steel crowbar with a curved claw, chipped red paint, a grip wrapped in leather strips, dents from many blows. |
| `hammer` | VORSCHLAGHAMMER | A sledgehammer with a massive square steel head, a long wooden handle wrapped near the end, spikes welded to one face. |
| `schockstab` | SCHOCKSTAB | A stun baton with two electrodes at the tip arcing with a small blue spark, a rubber grip and a battery housing with a teal indicator light. |
| `schlagring` | SCHLAGRING | A pair of heavy brass knuckles with worn studs, lying on a strip of cloth tape. |
| `kettensaege` | KETTENSÄGE | A compact chainsaw with a scratched engine housing, a long guide bar with sharp chain teeth, a pull cord and fuel stains. |
| `wurfmesser` | WURFMESSER | A fan of three balanced throwing knives with cord-wrapped handles, arranged in a leather holster. |
| `speer` | SPEER | A scavenged spear: a sharpened steel blade lashed to a long pole with wire and cloth, feathers and a small charm tied below the blade. |

## Wurfwaffen und Sprengstoff

| Kennung | Name im Spiel | Prompt (nach dem Stilblock) |
| --- | --- | --- |
| `granate` | GRANATE | A classic fragmentation hand grenade with a segmented olive body, a spoon lever and a pull ring, a little dust on the top. |
| `rauch` | RAUCHGRANATE | A cylindrical smoke grenade with a gray canister, a ring pull and a thin wisp of white smoke escaping from the top. |
| `blend` | BLENDGRANATE | A stun grenade with a perforated cylindrical body, bright white bands, a ring pull and a faint flash of light inside the holes. |
| `molotov` | MOLOTOW | A glass bottle filled with amber fuel, a burning cloth rag stuffed in the neck, soot on the glass. |
| `c4` | C4 | A block of plastic explosive wrapped in olive film, a detonator with two wires and a blinking red light, a small remote trigger beside it. |
| `haftladung` | HAFTLADUNG | A round sticky charge with a magnetic base and a glue rim, a timer dial on top and an amber indicator light. |
| `emp` | EMP-GRANATE | A grenade with a copper-wound core visible through a cage, a teal glow inside and small arcs of electricity. |
| `gas` | GASGRANATE | A canister grenade with yellow-green hazard bands, a valve on top leaking a thin greenish vapor. |
| `kuller` | KULLER | A heavy round grenade shaped like a bowling ball with grip grooves and a recessed fuse, meant to be rolled. |
| `knaller` | KNALLER | A bundle of three firecracker-like charges tied together with string, a single fuse sparkling at the end. |
| `schneeball` | SCHNEEBALL | A perfectly packed snowball with frost crystals, lying on a small piece of dark cloth, a cold blue light on it (a joke weapon). |

## Gegenstaende und Ausruestung

| Kennung | Name im Spiel | Prompt (nach dem Stilblock) |
| --- | --- | --- |
| `medkit` | MEDKIT | A rugged first-aid kit: a dented metal case with a faded cross shape, open, showing bandages, a syringe and a small bottle. |
| `munikiste` | MUNITIONSKISTE | An ammunition crate with a hinged lid, rope handles, stenciled stripes, brass cartridges spilling out. |
| `rpg_kiste` | RAKETENKISTE | A long wooden crate with a single rocket resting in foam padding, lid leaning against the side. |
| `sanitasche` | SANITASCHE | A medic satchel with a strap, a cross-shaped patch, pockets bulging with bandages and a tourniquet hanging out. |
| `munitionskiste` | MUNITIONSKISTE (STEHT) | A deployable ammo station: a tall metal box on short legs with open drawers of magazines and shells. |
| `geschuetz` | SELBSTSCHUSSANLAGE | A small automated sentry gun on a tripod, a boxy turret with a camera eye, an ammo belt and a teal status light. |
| `horchposten` | HORCHPOSTEN | A listening post: a tripod with a parabolic microphone dish, headphones hanging from it, a small antenna. |
| `drohne` | SPÄHDROHNE | A small four-rotor scout drone with a camera gimbal, scratched propellers and a blinking amber light. |
| `sprengfalle` | SPRENGFALLE | A pressure-plate landmine half buried in sand, with a thin tripwire variant beside it and a small warning flag. |
| `sandsackwand` | SANDSACKWAND | A short wall of stacked burlap sandbags, some torn and leaking sand, a few bullet holes. |
| `stacheldraht` | STACHELDRAHT | A coil of razor wire on wooden stakes, catching the light, a strip of torn cloth caught on a barb. |
| `kanister` | BENZINKANISTER | A red jerrycan full of fuel, dented and scratched, a spout attached, a drop of fuel on the cap. |
| `kraehenfuesse` | KRÄHENFÜSSE | A handful of steel caltrops scattered on sand, each with four sharp points, one in focus in the foreground. |
| `schild` | SCHILD | A tall riot shield made from scavenged steel plates riveted together, a narrow view slot, dents from many bullets. |
