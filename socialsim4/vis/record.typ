#import "./template.typ" : *

#set page(margin: 28pt)


// === Replace the content in `context` with any new transcript ===
#let ctx = read("chat.txt")

#set heading(numbering: none)

= Simple Chat

#parse-transcript(ctx, colors: theme)
