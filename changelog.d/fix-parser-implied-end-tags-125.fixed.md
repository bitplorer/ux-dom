- **`<p>one<p>two<p>three` is three paragraphs (#125).** The sanitized output
  used to nest them, and Chromium built five `<p>` from it. Sanitized output
  now parses in Chromium to the DOM of the input over the implied-end-tag
  corpus and 700 random nestings (71 of 411 differed before).
