#import "./template.typ" : *

#set page(margin: 28pt)


// === Replace the content in `context` with any new transcript ===
#let ctx = read("werewolf.txt")

#set heading(numbering: none)

= Werewolf

#parse-transcript(ctx, colors: theme)
