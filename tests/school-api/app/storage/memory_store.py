_next_student_seq = 1
_next_teacher_seq = 1


def new_student_id():
    global _next_student_seq
    student_id = f"S{_next_student_seq}"
    _next_student_seq += 1
    return student_id


def new_teacher_id():
    global _next_teacher_seq
    teacher_id = f"T{_next_teacher_seq}"
    _next_teacher_seq += 1
    return teacher_id


def _seed_teachers():
    seeds = [
        {"name": "Alan Turing", "email": "alan.turing@school.test", "subject": "Mathematics"},
        {"name": "Marie Curie", "email": "marie.curie@school.test", "subject": "Science"},
        {"name": "Jane Austen", "email": "jane.austen@school.test", "subject": "English"},
        {"name": "Howard Zinn", "email": "howard.zinn@school.test", "subject": "History"},
    ]
    teachers = []
    for seed in seeds:
        teachers.append({
            "id": new_teacher_id(),
            "name": seed["name"],
            "email": seed["email"],
            "subject": seed["subject"],
            "photo_url": None,
        })
    return teachers


def _seed_students():
    seeds = [
        {"name": "Liam Smith", "email": "liam.smith@school.test", "age": 14, "class_id": "C1"},
        {"name": "Olivia Brown", "email": "olivia.brown@school.test", "age": 15, "class_id": "C1"},
        {"name": "Noah Johnson", "email": "noah.johnson@school.test", "age": 13, "class_id": "C2"},
        {"name": "Emma Davis", "email": "emma.davis@school.test", "age": 14, "class_id": "C3"},
        {"name": "Ava Wilson", "email": "ava.wilson@school.test", "age": 16, "class_id": "C8"},
        {"name": "Ethan Moore", "email": "ethan.moore@school.test", "age": 15, "class_id": None},
    ]
    students = []
    for seed in seeds:
        students.append({
            "id": new_student_id(),
            "name": seed["name"],
            "email": seed["email"],
            "age": seed["age"],
            "class_id": seed["class_id"],
            "photo_url": None,
        })
    return students


students = _seed_students()
teachers = _seed_teachers()
