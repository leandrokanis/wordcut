from wordcut.processing.sentences import Sentence, split_sentences
from wordcut.transcript import Word


def test_a_word_ending_in_a_full_stop_closes_the_sentence_with_its_times_text_and_words() -> None:
    words = [Word("Deus", 0.0, 0.3), Word("governa.", 0.4, 0.9), Word("Mesmo", 1.0, 1.3)]

    assert split_sentences(words) == [
        Sentence(first_word=0, last_word=1, start=0.0, end=0.9, text="Deus governa."),
        Sentence(first_word=2, last_word=2, start=1.0, end=1.3, text="Mesmo"),
    ]


def starts(sentences: list[Sentence]) -> list[float]:
    return [sentence.start for sentence in sentences]


def test_a_pause_longer_than_one_and_a_half_seconds_starts_a_new_sentence() -> None:
    words = [Word("Mesmo", 0.0, 1.0), Word("calado", 2.501, 3.0), Word("Amém", 4.5, 5.0)]

    assert starts(split_sentences(words)) == [0.0, 2.501]


def words_in_a_row(count: int) -> list[Word]:
    return [Word(f"palavra{index}", float(index), index + 0.5) for index in range(count)]


def test_the_twenty_fifth_word_closes_the_sentence() -> None:
    sentences = split_sentences(words_in_a_row(26))

    assert [(sentence.first_word, sentence.last_word) for sentence in sentences] == [
        (0, 24),
        (25, 25),
    ]


def test_twenty_four_words_without_an_end_stay_one_sentence() -> None:
    assert len(split_sentences(words_in_a_row(24))) == 1


def test_no_words_make_no_sentences() -> None:
    assert split_sentences([]) == []
