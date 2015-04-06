Chronicle of Matthew of Edessa project - Transcription guidelines
======================================

Column and line recognition
------------------------
T-PEN is, for now, our transcription platform. Leads to a few considerations:

* Images should be straightened, cropped, unskewed etc. before they are uploaded! because they can't easily be replaced.
* If a line is still skewed, the base of the line should occur at the lowest point of that line (notwithstanding hanging characters).
* Marginalia are not given their own columns; rather, they are added at the point where they belong in the text flow.
 * Additions are marked as such, `place="margin-(left|right|top|bottom)"`
 * Comments, glosses, etc. are marked as `<note place="margin-*" type="(scribal|authorial)">` and, if they are not anchored into the text, `anchored="false"`.

Text division
-------------
* Mark divisions where they happen with the `<hi>` tag.
* Insert a `<milestone unit="section" n="YEAR"/>` tag at the beginning of each year-specific entry, where `n` is the number of the Armenian year in question. There will also be some intra-year milestones (e.g. marking the beginning of the letter of Tzimiskes) to be settled based on the capability of the collation engine.
* TODO decide how to represent section markers that appear in the manuscript.

Special characters
------------------
* Mark ideograms and ligatures that form a single glyph. In T-PEN, in the normal case, this is done simply by marking a `<g>` tag around the characters that the glyph would normalize to.
* If an ideogram is followed by seemingly redundant characters (e.g. [erkir]իր), or if a ligature appears to stand for a different set of characters than usual (e.g. the պտ ligature in place of պետ), we mark it like so:

    <g ref="երկիր">երկ</g>իր
	
* If the glyph has not been seen in any other manuscript so far, it needs to go into __some list__.

Punctuation
-----------
* Distinction between , and . is handled on a manuscript-by-manuscript basis, depending on whether any distinction can be perceived in the hand being transcribed. A note should be included in the transcription indicating the decision that was made.
* If a manuscript emerges that seems to make substantial use of the Armenian ՝ character, we will begin to use that character in our transcriptions. So far this has not been the case.
* Other accents are marked with the Armenian ՛ character following the closest vowel where they occur.
* Line breaks, when they appear, are marked with the Armenian ֊ character.
* Apostrophes before ի are not marked, although they are taken into consideration when the text is transcribed, to determine whether a word boundary has occurred.


Abbreviations
-------------
* Mark abbreviations with the `<abbr>` tag. In general we do not supply the expansion in the transcription; this will be done during the collation phase.
* The tag should surround the letters marked in the abbreviation, rather than the whole word (unless the whole word is marked.) This is in many cases approximate at best.
* We do not distinguish between different forms of abbreviation (e.g. line above vs. two hatch marks). Likewise, if there are two contiguous abbreviation marks in a word, they can be represented as a single abbreviation.

Corrections
----------

* If the correction is a replacement, it goes into a `<subst><del/><add/></subst>` construct.
* We note the mechanism used to do the correction in the `rend` attribute, placed on whichever element is appropriate. Values currently in use include:
 * cancel
 * scribble
 * erase
 * overwrite
 * rewrite
 * partial (part written, incomplete)
 * blot [TODO check: is this really a gap?]
 * strike (scratch, crossout)
 * complicated
 * reinterpretation
 * marginal
 * implicit overwrite
 * rewrite

* We note a `place` for any added text, unless it is in a `<subst rend="overwrite">`. Possible values for place include:
 * infralinear (below)
 * supraliner (above)
 * margin
 * inline
 * afterline
 * beforeline

* For missing highlights TODO do we mark a gap or a supplied?

Numbers
-------
* Entering the value is optional if the number is straightforward - we have a script for that.
* Periods(semicolons) around numbers should be assumed to be part of the number representation.
* If the number is marked with a line over it, record the line like so: ե՟ or խ՟ռ՟.
* Record the whole number, e.g. դ՟ճ՟ և է՟ all goes in the tag, with value 407.
* If the number is declined explicitly, the declination goes outside the number tag *only* if it is the last part of the number. e.g. `<num value="12">բ՟ժ՟</num>աց` but `<num value="12000">բ՟ժ՟աց ռ՟</num>`.
