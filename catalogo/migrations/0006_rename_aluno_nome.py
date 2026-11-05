from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0005_aluno"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Aluno",
            new_name="Nome",
        ),
        migrations.AlterModelOptions(
            name="nome",
            options={
                "ordering": ["nome"],
                "verbose_name": "nome",
                "verbose_name_plural": "nomes",
            },
        ),
    ]
