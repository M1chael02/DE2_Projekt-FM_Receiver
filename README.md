# DE2_Projekt-FM_Receiver
Jednoduchý přijímač FM stanic řízený mikrokontrolérem RPi Pico W

## Členové týmu
- Marek Hostášek - SPI Displej 
- Michael Jurča - FM Tuner
- Denis Kaňovský - Integrace rotačního enkodéru

## Obsah
- [Základní popis fungování](#Základní-popis-fungování)
- [Blokové schéma](#Blokové-schéma)
- [Schéma](#Schéma)
- [I/O sekce](#IO-sekce)
- [Použité zdroje](#Použité-zdroje)

## Blokové schéma
![Image of diagram](https://github.com/M1chael02/DE2_Projekt-FM_Receiver/blob/main/images/blok_FM.png)

## Schéma
![Image of schematic](https://github.com/M1chael02/DE2_Projekt-FM_Receiver/blob/main/images/schematic.png)


## Hardware

| Součástka | Model | Odkazy |
|:-----:|-----| :---: |
| Mikrokontrolér | Raspberry Pi Pico W | [Odkaz na datasheet](https://pip-assets.raspberrypi.com/categories/686-raspberry-pi-pico-w/documents/RP-008312-DS-3-pico-w-datasheet.pdf) |
| Rotační enkodér | Okystar KY-040 | [Odkaz na datasheet](https://okystar.com/wp-content/uploads/2017/08/OKY3431.pdf) |
| FM tuner | Si4703 | [Odkaz na datasheet](https://cdn.sparkfun.com/assets/learn_tutorials/2/7/4/Si4703_datasheet.pdf) |
| LCD displej | Displej z Nokia 5110 | [Odkaz na datasheet řadiče PCD8544](https://cdn.sparkfun.com/assets/b/1/b/e/f/Nokia5110.pdf) |


Rotační enkodér:
Okystar KY-040
https://botland.store/encoders/16558-rotation-sensor-encoder-20-pulses-okystar-ky-040-5904422366278.html

FM tuner:
Si4703
https://www.pololu.com/product/1647

LCD displej:
Nokia5110
https://www.hadex.cz/p/m507a-displej-lcd-84x48-znaku-nokia5110-modre-podsviceni-cervena-dps?hgtid=c521c699-b283-4806-b29b-63bd0b512dd7

Raspberry Pi Pico W

## Základní popis fungování

## I/O sekce

## Použité zdroje
https://cdn.shopify.com/s/files/1/0672/9409/files/ky-040-rotary-encoder-datasheet-and-tutorial.pdf
https://www.alldatasheet.net/datasheet-pdf/pdf/18170/PHILIPS/PCD8544.html
https://www.kutilovo.cz/shop/files/21911.pdf
