# Recourse mark

The mark is the product in one shape: one path out, a half turn, one path
returning underneath, with the arrowhead against the flow. It is the still
frame of the hero canvas, where a lane of payment ticks drifts one way and
one of them travels back.

## Geometry

Drawn once, on a 32 unit grid. Everything else in this pack is that one path
at a different size or colour.

    viewBox      0 0 32 32
    path         M7 11H21A6 6 0 0 1 21 23H7M11.5 18.5L7 23L11.5 27.5
    stroke       2.6 units, 8.1 percent of the box
    linecap      square
    arc          r6, centred at 21,17, a true half turn
    arrowhead    two 45 degree legs, the only diagonals in the mark
    fill         none, at every size

The favicon variant is the same path at stroke 3.4, because below 20px the
2.6 stroke lands between device pixels and greys out.

## Colour

One accent, and it is the only colour.

    cyan         #22D3EE    on the dark ground, the default
    ink          #EEF3F8    on cyan, on photography, on any busy ground
    ground       #0A0C12    on light or cyan fills
    currentColor              for inline SVG that should inherit its context

No gradient, no glow, no bevel, no second hue. If a ground makes cyan hard to
read, use ink rather than tinting the mark.

## Clear space and minimum size

Clear space is 4 units on the 32 grid, so one eighth of the mark's width on
every side. Nothing enters it, including the wordmark: the lockups already
carry it.

Minimum size is 16px. Below that, use the favicon variant or nothing.

## Files

    svg/mark-cyan.svg              the default
    svg/mark-ink.svg               light mark for busy or cyan grounds
    svg/mark-ground.svg            dark mark for light grounds
    svg/mark-currentcolor.svg      inherits colour from its context
    svg/favicon.svg                stroke 3.4, for 16 to 20px
    svg/lockup-horizontal.svg      mark and wordmark, navbar proportions
    svg/lockup-stacked.svg         mark over wordmark, centred

    png/mark-cyan-*.png            transparent, 16 to 1024
    png/mark-ink-512.png           transparent
    png/mark-cyan-on-ground-*.png  on #0A0C12, squared
    png/favicon-16.png             stroke 3.4
    png/favicon-32.png             stroke 3.4
    png/favicon-48.png             stroke 3.4
    png/apple-touch-icon-180.png   on #0A0C12, no padding added
    png/lockup-horizontal.png      rendered with Source Serif 4
    png/lockup-stacked.png         rendered with Source Serif 4

The two lockup SVGs carry live text, so they need Source Serif 4 to render as
intended. The lockup PNGs were rendered with the font loaded; use those
wherever the font cannot be guaranteed.

## The wordmark

RECOURSE, Source Serif 4, weight 600, letterspaced 0.22em, in ink. All caps,
never mixed case, never italic. The italic is the site's display voice and
belongs to headings, not to the wordmark.

## The circle

The navbar used to draw a 1px circle around a placeholder R. Drop it. The
circle existed to give a bare letter an edge to sit against, and a mark that
is already a closed shape does not need one; the ring also puts a second
radius into a page whose corners are square. Keep a 38px box for the tap
target and let the fold be the only arc in the bar.

## Do not

    recolour the mark outside the four files above
    outline, shadow, or glow it
    place it inside a circle, a rounded square, or any badge
    stretch it: the box is square at every size
    rotate or mirror it, the direction of return is the meaning
    set the wordmark in the serif italic, or in mono, or in sentence case
    redraw the arrowhead at any angle other than 45 degrees
