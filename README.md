# DE2_Projekt-FM_Receiver
Jedná se o frekvenčně modulovaný (FM) rozhlasový přijímač, pracující na velmi krátkých vlnách (VKV). Je přeladitelný v celém pásmu CCIR (západní norma) 87,5 MHz až 108 MHz. Disponuje systémem doplňkových informací RDS (Radio Data System). K řízení je použitý jednodeskový počítač Raspberry Pi Pico.

## Členové týmu
- Marek Hostášek - SPI Displej 
- Michael Jurča - FM Tuner
- Denis Kaňovský - Integrace rotačního enkodéru

## Obsah
- [Blokové schéma](#Blokové-schéma)
- [Schéma](#Schéma)
- [Hardware](#Hardware)
- [Základní popis fungování](#Základní-popis-fungování)
- [I/O sekce](#IO-sekce)
- [Použité knihovny](#Použité-knihovny)
- [Použité zdroje](#Použité-zdroje)

## Blokové schéma
![Image of diagram](https://github.com/M1chael02/DE2_Projekt-FM_Receiver/blob/main/images/blok_FM.png)

## Schéma
![Image of schematic](https://github.com/M1chael02/DE2_Projekt-FM_Receiver/blob/main/images/schematic.png)


## Hardware

| Součástka | Model | Odkazy |
| :-----:|-----| :---: |
| Mikrokontrolér | Raspberry Pi Pico W | [Odkaz na datasheet](https://pip-assets.raspberrypi.com/categories/686-raspberry-pi-pico-w/documents/RP-008312-DS-3-pico-w-datasheet.pdf) |
| Rotační enkodér | Okystar KY-040 | [Odkaz na datasheet](https://okystar.com/wp-content/uploads/2017/08/OKY3431.pdf) |
| FM tuner | Si4703 | [Odkaz na datasheet](https://cdn.sparkfun.com/assets/learn_tutorials/2/7/4/Si4703_datasheet.pdf) |
| LCD displej | Displej z Nokia 5110 | [Odkaz na datasheet řadiče PCD8544](https://cdn.sparkfun.com/assets/b/1/b/e/f/Nokia5110.pdf) |


## Základní popis fungování
Rozhlasový přijímač je vybarven LCD displejem a ovládá se pomocí rotačního enkodéru. Stiskem enkodéru se můžeme přepínat mez dvěma režimy. Prvním z nich je regulace hlasitosti, druhým změna frekvence (s krokem 0,1 MHz). Na displeji se zobrazuje od shora dolů:
- hlasitost
- frekvence (MHz)
- doplňkové informace (RDS) – střídavě název stanice a radiotext

Audio výstup přijímače je řešen pomocí konektoru Jack 3,5 mm, přičemž kabel připojeného zařízení slouží současně jako anténa. K napájení celého zařízení slouží micro USB B kabel připojený do Raspberry Pi Pico, ze kterého jsou následně napájeny i ostatní moduly.


## I/O sekce


## Použité knihovny
| Knihovna | Odkazy |
| :-----: | :---: |
| machine | [Odkaz](https://docs.micropython.org/en/latest/library/machine.html) |
| time | [Odkaz](https://docs.micropython.org/en/latest/library/time.html) |
| framebuf | [Odkaz](https://docs.micropython.org/en/latest/library/framebuf.html) |


## Použité zdroje
| Odkaz |
|:-----:|
| [Arduino Rotary Encoder User Manual](https://cdn.shopify.com/s/files/1/0672/9409/files/ky-040-rotary-encoder-datasheet-and-tutorial.pdf) |
| [Claude (AI)](https://claude.ai/) |
| [Raspberry Pi Pico Pinout](https://pico.pinout.xyz/) |
