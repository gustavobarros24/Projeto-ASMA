#let blue = rgb("365F91")
#let gray = rgb("808080")
#let light_gray = rgb("A6A6A6")

#let cover(title: "", authors: [], string_date) = {
  let render_authors = grid(columns: authors.len(),
    column-gutter: -180pt,
    ..authors.map(it => [
      #image(it.image, width: 30%)
      #text(size:10pt, weight: "bold", it.name) \
      #text(size: 10pt, it.number)
    ])
   )
                           
  {
    set page(paper: "a4", margin: (x: 0cm,y: 0cm))
    
    rect(fill: blue,height: 100%, width:23.3%)
    
    place(bottom + left,dx: 15pt,dy:-40pt, {
      text(weight:"bold", size: 100pt, fill: blue, [>])
      text(weight:"bold", size: 100pt, fill: white, [A])
      text(weight:"bold", size: 100pt, fill: blue, [S])
      text(weight:"bold", size: 100pt, fill: blue, [M])
      text(weight:"bold", size: 100pt, fill: blue, [A])


    })
  
    {
      set place(top+left, dx: 150pt)
      place(dy: 120pt, image("Photos/uminho.jpg", height: 8%))
      place(dy: 200pt, {
        text(size: 10pt, weight: "bold", fill: gray, [Universidade do Minho\ ])
        text(size: 9pt, fill: gray, [Escola de Engenharia\ Mestrado em Engenharia Informática\ ])
      })
      place(dy: 300pt, {
  
        text(size: 20pt, fill: blue, weight: "bold", [Unidade Curricular de \ Agentes e Sistemas Multiagente\ ])
        text(size: 10pt, [\ Ano Letivo de 2025/2026])
         

        
      })
      place(dy: 460pt, text(size: 20pt, weight: "bold", title))
      place(dy: 530pt, render_authors)
      
      place(dy: 680pt, text(size: 12pt, string_date))
    }
  }
  
}