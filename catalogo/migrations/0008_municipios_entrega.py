from decimal import Decimal

from django.db import migrations


MUNICIPIOS = (
    ("Recife", 2611606),
    ("Olinda", 2609600),
    ("Jaboatão dos Guararapes", 2607901),
    ("Paulista", 2610707),
    ("Camaragibe", 2603454),
)


def criar_municipios(apps, schema_editor):
    AreaEntrega = apps.get_model("catalogo", "AreaEntrega")
    database = schema_editor.connection.alias
    for municipio, codigo_ibge in MUNICIPIOS:
        AreaEntrega.objects.using(database).get_or_create(
            codigo_ibge=codigo_ibge,
            defaults={
                "municipio": municipio,
                "taxa_entrega": Decimal("10.00"),
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0007_pedido_pedidoitem"),
    ]

    operations = [
        migrations.RunPython(criar_municipios, migrations.RunPython.noop),
    ]
