# Brincando um pouco mais com o SSH, SCP e rsync

_Atualizado em 07/07/2026_

~/.ssh/config

Host nome-do-host
    HostName 192.168.0.1
    User Puff
    IdentityFile ~/.ssh/id_ed25519
   



rsync -avz (a guarda as permiões, v verbose , z compactar) --progress dir1 vm-lab-01
rsync -avz --progress --exclude='.git' /dir1 vm-lab-01:~/


 

