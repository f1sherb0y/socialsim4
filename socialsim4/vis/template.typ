#let theme = (
  action: rgb("#1e88e5"),      // Renamed from public-event for clarity
  message-tag: rgb("#8e24aa"), // Renamed from message for clarity
  sender: rgb("#2e7d32"),
  content: rgb("#263238"),
)

#let render-multiline = (s, fill: theme.content) => {
  for part in s.trim().split("\n") {
    text(fill: fill)[#part]
    linebreak()
  }
}

// MODIFIED: Takes `event-type` to display tags like [web_search]
#let event-block = (event-type, content, colors: theme) => [
  #text(fill: colors.action)[[#event-type]]
  #h(8pt)
  #render-multiline(content, fill: colors.content)
]

// DELETED: public-event-block is no longer needed.

// MODIFIED: Changed the hardcoded label from "Message" to "send_message"
#let message-block = (sender, msg, colors: theme) => [
  #text(fill: colors.message-tag)[[message]]
  #h(8pt)
  #text(fill: colors.sender)[#sender :]
  #linebreak()
  #h(16pt)
  #render-multiline(msg, fill: colors.content)
]

// --- MODIFIED: All old regexes are replaced with two new, general ones. ---
#let re-tagged-line = regex("^\s*\[(.*?)\]\s*(.*)$")
#let re-sender-msg = regex("(?s)^(.+?):\s*(.*)$")
// --- End of regex modification ---

#let parse-transcript = (raw, colors: theme) => {
  let blocks = ()

  // Accumulators for current block
  let kind = none
  let sender = ""
  let buf = ""
  let event_type = "" // ADDED: State for the current event's tag

  for raw-line in raw.replace("\r\n", "\n").split("\n") {
    let stripped = raw-line.trim()

    // --- MODIFIED: The main trigger logic ---
    let m-tagged = stripped.match(re-tagged-line)

    if m-tagged != none {
      // Commit ongoing block (logic is the same, but call is modified)
      if kind == "event" {
        blocks.push(event-block(event_type, buf, colors: colors))
      } else if kind == "message" {
        blocks.push(message-block(sender, buf, colors: colors))
      }

      // Start new block from the single generic match
      let tag = m-tagged.captures.at(0)
      let content = m-tagged.captures.at(1)

      if tag == "send_message" {
        kind = "message"
        let sender_match = content.match(re-sender-msg)
        if sender_match != none {
          sender = sender_match.captures.at(0).trim()
          buf = sender_match.captures.at(1).trim()
        } else {
          sender = "Unknown" // Fallback for malformed message
          buf = content
        }
      } else if tag == "speak" {
        kind = "message"
        let sender_match = content.match(re-sender-msg)
        if sender_match != none {
          sender = sender_match.captures.at(0).trim()
          buf = sender_match.captures.at(1).trim()
        } else {
          sender = "Unknown" // Fallback for malformed message
          buf = content
        }
      } 
      else {
        kind = "event"
        event_type = tag
        buf = content
      }
      continue
    }
    // --- End of main trigger modification ---

    // Continuation of current block: this logic is unchanged and correct.
    if buf != "" { buf += "\n" }
    buf += raw-line
  }

  // Commit the trailing block (logic is the same, but call is modified)
  if kind == "event" {
    blocks.push(event-block(event_type, buf, colors: colors))
  } else if kind == "message" {
    blocks.push(message-block(sender, buf, colors: colors))
  }

  // Render with some vertical spacing between blocks
  [
    #for b in blocks {
      b
      v(10pt)
    }
  ]
}