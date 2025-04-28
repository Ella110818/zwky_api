from django.db import models

# Create your models here.
class Face(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)
    feat = models.BinaryField(null=False)
    
    class Meta:
        db_table = 'faces'
        
    def __str__(self):
        return self.name
