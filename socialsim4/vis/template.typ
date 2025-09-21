
#let theme = (
  public-event: rgb("#1e88e5"),  // Public event label
  message: rgb("#8e24aa"),       // "[Message]" label
  sender: rgb("#2e7d32"),        // Sender name
  content: rgb("#263238"),       // Message/content text
)

#let render-multiline = (s, fill: theme.content) => {
  for part in s.split("\n") {
    text(fill: fill)[#part]
    linebreak()
  }
}

// A generic event block (no "Public Event:" label)
#let event-block = (content, colors: theme) => [
  #text(fill: colors.public-event)[Event:]
  #h(8pt)
  #render-multiline(content, fill: colors.content)
]

// A public event block with a colored label
#let public-event-block = (content, colors: theme) => [
  #text(fill: colors.public-event)[Public Event:]
  #h(8pt)
  #render-multiline(content, fill: colors.content)
]

#let message-block = (sender, msg, colors: theme) => [
  #text(fill: colors.message)[[Message]]
  #h(8pt)
  #text(fill: colors.sender)[#sender]
  #text(fill: colors.content)[:]
  #linebreak()
  #h(16pt)
  #render-multiline(msg, fill: colors.content)
]

#let re-msg = regex("^\\s*\\[Message\\]\\s*(.*?):\\s*(.*)$")
#let re-public = regex("^\\s*Public Event:\\s*(.*)$")
#let re-host-brief = regex("^\\s*Host requested brief:.*$")
#let re-searched = regex("^\\s*(.+?)\\s+searched:\\s*(.*)$")
#let re-viewed = regex("^\\s*(.+?)\\s+viewed web page:\\s*(.*)$")

#let parse-transcript = (raw, colors: theme) => {
  let blocks = ()

  // Accumulators for current block
  let kind = none          // "public" | "event" | "message" | none
  let sender = ""
  let buf = ""

  // Line-based scan that splits on markers and preserves intermediate lines
  for raw-line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n") {
    let stripped = raw-line.trim()

    // Evaluate regex markers
    let m-msg = stripped.match(re-msg)
    let m-public = stripped.match(re-public)
    let m-host = stripped.match(re-host-brief)
    let m-searched = stripped.match(re-searched)
    let m-viewed = stripped.match(re-viewed)

    if m-msg != none or m-public != none or m-host != none or m-searched != none or m-viewed != none {
      // Commit ongoing block
      if kind == "public" {
        blocks += (public-event-block(buf, colors: colors),)
      } else if kind == "event" {
        blocks += (event-block(buf, colors: colors),)
      } else if kind == "message" {
        blocks += (message-block(sender, buf, colors: colors),)
      }

      // Start new block from matches
      if m-msg != none {
        kind = "message"
        sender = m-msg.captures.at(0).trim()
        buf = m-msg.captures.at(1).trim()
      } else if m-public != none {
        kind = "public"
        buf = m-public.captures.at(0).trim()
      } else if m-host != none {
        // Treat host requests as generic events (not public events)
        kind = "event"
        buf = stripped
      } else if m-searched != none or m-viewed != none {
        // Treat searched/viewed as generic events (not public events)
        kind = "event"
        buf = stripped
      }
      continue
    }

    // Continuation of current block: preserve original spacing
    if buf != "" { buf += "\n" }
    buf += raw-line
  }

  // Commit the trailing block
  if kind == "public" {
    blocks += (public-event-block(buf, colors: colors),)
  } else if kind == "event" {
    blocks += (event-block(buf, colors: colors),)
  } else if kind == "message" {
    blocks += (message-block(sender, buf, colors: colors),)
  }

  // Render with some vertical spacing between blocks
  [
    #for b in blocks {
      b
      v(10pt)
    }
  ]
}