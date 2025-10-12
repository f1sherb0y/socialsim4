#import "./template.typ" : *

#set page(margin: 28pt)


// === Replace the content in `context` with any new transcript ===
#let ctx = read("chat2.txt")

#set heading(numbering: none)

= Simple Chat Scene

#parse-transcript(ctx, colors: theme)
