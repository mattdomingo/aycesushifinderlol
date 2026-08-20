# Sushi Finder Lol

Yum — a simple place to explore sushi.

## A brief history of sushi

Sushi began in Southeast Asia as a method of preserving fish: fish was packed
with fermented rice, and the rice was originally discarded before eating. The
practice traveled to Japan, where it developed into *narezushi*.

Over time, Japanese cooks shortened the fermentation process and began serving
the rice alongside the fish. During the Edo period (1603–1868), Edo-style
*nigiri sushi* emerged in what is now Tokyo as a quick, hand-formed meal. It
eventually became the style most people recognize today.

Modern sushi includes far more than raw fish. Nigiri, maki rolls, chirashi, and
vegetable-based options all reflect regional traditions and new interpretations
of this long-evolving cuisine.

## Pricing API

The lightweight backend uses only Python's standard library. Start it with:

```bash
python sushi.py serve
```

It serves `GET /health`, `GET /api/menu`, and `POST /api/quote`. A quote body
contains a `service` (`lunch` or `dinner`), a positive integer `guests`, and an
optional non-negative integer `leftover_pieces`.

```json
{"service":"dinner","guests":2,"leftover_pieces":3}
```
