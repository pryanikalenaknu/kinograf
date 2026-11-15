"""Невеликий тестовий набір фільмів, персоналій, жанрів і нагород."""

from datetime import date

from kinograf.models import Award, Film, Genre, Participation, Person, Role

POSTER = "http://commons.wikimedia.org/wiki/Special:FilePath/"

FILMS = [
    Film("Q1", "Плем'я", date(2014, 5, 21), 132, POSTER + "Plemya.jpg"),
    Film("Q2", "Земля блакитна, ніби апельсин", date(2020, 1, 25), 74),
    Film("Q3", "Мамай", date(2003, 1, 1), 80),
    Film("Q4", "Поводир", date(2014, 11, 13), 122, POSTER + "Povodyr.jpg"),
    Film("Q5", "Атлантида", date(2019, 9, 4), 108),
    Film("Q6", "Відблиск", date(2021, 9, 1), 127),
    Film("Q7", "Їжак", date(1995, 3, 1)),
]

PEOPLE = {
    person.qid: person
    for person in [
        Person("Q10", "Мирослав Слабошпицький"),
        Person("Q11", "Олесь Санін"),
        Person("Q12", "Валентин Васянович"),
        Person("Q13", "Андрій Римарук"),
        Person("Q14", "Алла Загайкевич"),
        Person("Q15", "Ірина Цілик"),
        Person("Q16", "Яна Новікова"),
    ]
}

PARTICIPATIONS = [
    Participation(film, person, role)
    for film, person, role in [
        ("Q1", "Q10", Role.DIRECTOR),
        ("Q1", "Q10", Role.SCREENWRITER),
        ("Q1", "Q16", Role.CAST),
        ("Q2", "Q15", Role.DIRECTOR),
        ("Q3", "Q11", Role.DIRECTOR),
        ("Q3", "Q11", Role.SCREENWRITER),
        ("Q3", "Q14", Role.COMPOSER),
        ("Q4", "Q11", Role.DIRECTOR),
        ("Q4", "Q11", Role.SCREENWRITER),
        ("Q4", "Q14", Role.COMPOSER),
        ("Q5", "Q12", Role.DIRECTOR),
        ("Q5", "Q12", Role.SCREENWRITER),
        ("Q5", "Q13", Role.CAST),
        ("Q6", "Q12", Role.DIRECTOR),
        ("Q6", "Q13", Role.CAST),
    ]
]

DRAMA = Genre("Q130232", "драма")
DOCUMENTARY = Genre("Q93204", "документальний фільм")
HISTORICAL = Genre("Q17013749", "історичний фільм")

GENRES = {
    "Q1": [DRAMA],
    "Q2": [DOCUMENTARY],
    "Q3": [DRAMA, HISTORICAL],
    "Q4": [DRAMA, HISTORICAL],
    "Q5": [DRAMA],
    "Q6": [DRAMA],
}

AWARDS = {
    "Q2": [Award("Q100", "Премія «Сандерс»")],
    "Q5": [Award("Q101", "Венеційський кінофестиваль — найкращий фільм програми «Горизонти»")],
}
