from django.db import migrations


def seed(apps, schema_editor):
    def manager(model):
        return apps.get_model("assessments", model).objects.using(schema_editor.connection.alias)

    program = manager("AcademicProgram").create(code="BSIT", name="BS Information Technology")
    subject = manager("Subject").create(program=program, code="DB-FND", name="Database Foundations (prototype)")
    for code, name, description in [
        ("DB-01", "Distinguish primary and foreign keys", "Explain how a primary key identifies a row and how a foreign key links rows."),
        ("DB-02", "Interpret relationship cardinality", "Read one-to-many and many-to-many relationships in an ERD."),
        ("DB-03", "Write a basic SQL join", "Select fields from related tables by matching the appropriate keys."),
    ]:
        competency = manager("Competency").create(code=code, name=name, description=description)
        manager("SubjectCompetency").create(subject=subject, competency=competency)


class Migration(migrations.Migration):
    dependencies = [("assessments", "0001_initial")]
    operations = [migrations.RunPython(seed)]
