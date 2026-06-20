# ASCII Art Visualization Modes

Questo progetto contiene multiple modalità di visualizzazione per ASCII art, tutte basate sul file `text.md` che contiene diverse sezioni di ASCII art.

## Modalità Disponibili

### 1. Cascade (cascata.py)
Effetto a onda orizzontale che muove l'arte in modo fluido e ondulatorio.

### 2. Shadow (ombra.py)
Effetto ombra animata che crea un'ombra dinamica sotto l'ASCII art.

### 3. Blink (lampeggiante.py)
Effetto di lampeggiamento random che fa brillare i pixel in modo casuale.

### 4. Wave (onda.py)
Movimento ondulatorio fluido che muove l'arte su e giù.

### 5. Pulse (pulsazione.py)
Effetto di pulsazione radiale che parte dal centro dell'arte.

### 6. Glitch (glitch.py)
Effetto glitch digitale con distorsioni e artefatti casuali.

### 7. Zoom (zoom.py)
Effetto di zoom che ingrandisce e rimpicciolisce l'arte periodicamente.

## Utilizzo

### Launcher Principale
```bash
python launcher.py <modalità> [opzioni]
```

### Esempi
```bash
# Lista tutte le modalità disponibili
python launcher.py --list-modes

# Lista tutte le sezioni di ASCII art disponibili
python launcher.py --list-sections

# Esegui modalità cascade
python launcher.py cascade

# Esegui modalità blink su una sezione specifica
python launcher.py blink --section SKULL

# Esegui modalità wave e stampa i frame una sola volta
python launcher.py wave --once

# Esegui con crop per adattare al terminale
python launcher.py pulse --crop
```

### Opzioni Comuni
- `--source <file>`: Specifica un file diverso da text.md
- `--once`: Stampa i frame una sola volta invece di animare
- `--check`: Valida senza animare
- `--crop: Adatta i frame alla dimensione del terminale
- `--section <nome>`: Usa una sezione specifica di ASCII art

## Struttura del File text.md

Il file `text.md` contiene multiple sezioni di ASCII art, ognuna identificata da un titolo (es. SKULL, HEART, DRAGON, ecc.). Le sezioni sono separate da linee di testo ripetuto che fungono da separatori.

## Aggiungere Nuove Modalità

Per aggiungere una nuova modalità:
1. Crea un nuovo file Python nella cartella `imputs/`
2. Implementa le funzioni `render_frame`, `build_frames`, `validate`, `animate`
3. Aggiungi la modalità al dizionario `MODES` in `launcher.py`

## Sezioni ASCII Art Disponibili

- SKULL
- HEART
- DRAGON
- STAR
- CROWN
- BUTTERFLY
- FISH
- TREE
- MOON
- CLOUD
- LIGHTNING
- ARROW
- FLOWER
- BIRD
- CAT, DOG, HORSE, LION, ELEPHANT
- SNAKE, SPIDER, SCORPION
- WOLF, BEAR, RABBIT, FOX, DEER
- OWL, EAGLE, SWAN, PEACOCK, FLAMINGO, PARROT, PENGUIN
- DOLPHIN, WHALE, SHARK, TURTLE, FROG
- T-REX, ROBOT, ALIEN, GHOST, ZOMBIE, VAMPIRE, WITCH, WIZARD
- KNIGHT, PIRATE, NINJA, SAMURAI, CYBORG, MECH, TANK
- PLANE, BOAT, CAR, TRAIN, ROCKET
- GUN, SWORD, SHIELD
- E molte altre...

## Requisiti

- Python 3.7+
- Terminale con supporto UTF-8
- Su Windows: il terminale deve supportare caratteri Unicode

## Come Funziona

Ogni modalità:
1. Carica l'ASCII art dal file `text.md`
2. Genera una sequenza di frame (di solito 60-100 frame)
3. Ogni frame applica una trasformazione diversa all'arte
4. I frame vengono animati in loop continuo
5. Supporta Ctrl+C per interrompere l'animazione

Le modalità usano matematica (seni, coseni, funzioni d'onda) per creare effetti fluidi e naturali.