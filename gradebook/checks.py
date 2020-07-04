from cs50 import SQL

db = SQL("sqlite:///gradebook.db")

grades = db.execute("SELECT grade FROM grades WHERE student_name = :student_name AND class_name = :class_name AND Id = :Id",
                Id=1, student_name="Harry Potter", class_name=302)

grade = []

for i in range(len(grades)):
    grade.append(grades[i]["grade"])
                
avg_grade = float(sum(grade)/len(grade))

print(avg_grade)