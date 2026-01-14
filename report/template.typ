#let project(body) = {
  // Set the document's basic properties.
  set page(paper: "a4", margin:(top: 2.5cm, bottom: 2.5cm, left: 3cm, right: 3cm))
    set text(font: "Calibri", lang: "pt", region: "PT", size: 12pt)

  // Main body.
  set par(justify: true)
  
  // Remove dots from outlines
  set outline()

  set heading(numbering: "1.")
  
  show heading: it => {
    if it.level == 1 {
      //pagebreak()
      block(
        above: 2pt,
        below: 2pt,
      )
    }
    it
  }

  show raw.where(block: false): box.with(
    fill: luma(240),
    inset: (x: 3pt, y: 0pt),
    outset: (y: 3pt),
    radius: 2pt,
  )

  // Display block code in a larger block
  // with more padding.
  show raw.where(block: true): block.with(
    breakable: true,
    fill: luma(240),
    inset: 15pt,
    radius: 4pt,
  )

  

  show heading: set block(above: 2em, below: 1em)

  show link: set text(fill: blue.darken(30%))
  show link: underline.with(evade: false)
  

  show figure.where(kind: "attachment"): it => {
    heading(outlined: false, numbering: none, level: 2)[#it.caption]
    it.body
  }

  show heading.where(level: 1): it => { text(size: 18pt, it) }
  show heading.where(level: 2): it => { text(size: 16pt, it) }
  show heading.where(level: 3): it => { text(size: 14pt, it) }
  show heading.where(level: 4): it => { text(size: 12pt, it) }
  
  body
}

  



#let attachment = figure.with(kind: "attachment", numbering: "1", supplement: [Anexo])