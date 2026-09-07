from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_services', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='pet',
            name='available',
            field=models.BooleanField(default=True),
        ),
    ]
