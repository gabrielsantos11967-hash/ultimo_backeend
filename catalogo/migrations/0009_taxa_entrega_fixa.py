from decimal import Decimal

from django.db import migrations


def fixar_taxa_entrega(apps, schema_editor):
    AreaEntrega = apps.get_model("catalogo", "AreaEntrega")
    Pedido = apps.get_model("catalogo", "Pedido")
    database = schema_editor.connection.alias

    AreaEntrega.objects.using(database).all().update(
        taxa_entrega=Decimal("10.00")
    )
    Pedido.objects.using(database).all().update(
        taxa_entrega=Decimal("10.00")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0008_municipios_entrega"),
    ]

    operations = [
        migrations.RunPython(fixar_taxa_entrega, migrations.RunPython.noop),
    ]
