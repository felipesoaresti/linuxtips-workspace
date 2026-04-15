# Instalando o Ubuntu com LVM

_Exportado em 15/04/2026_

LVM - Logical volume manager --> Uma partição que aumenta e diminui o espaço
- Adicionar discos sem desligar
- Expandir/Reduzir volumes online ( sem reboot )
- Mover dados entre os discos sem parar o serviço 
- os discos de Cloud são LVM

Ext4 - Sistema de arquivos 
Xfs -  sistemas de arquivos 

PV - Physical volume - disco ou parição que o LVM controla /dev/sda(1,2,3,)
VG - Volume Group - Pool de espaço formado por um ou mais PVs  
LV - Logical volume - Partição virtual criada dentro do VG/ onde vai o FS 
 
comandos 


# pvdisplay
# vgdisplay
# lvdisplay
# df -h 

# Expansão de LV (para usar 100% livre do espaço do VG) Obs: resize2fs ext4/ext3
lvextend -l 100%FREE /dev/mapper/ubuntu--vg-ubuntu--lv
resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv 

# Para xfs --> xfs_growfs 
 



