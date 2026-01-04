export CR_PAT=<pat> # For Windows, use 'set CR_PAT=YOUR_PAT_HERE'
echo $CR_PAT | docker login ghcr.io -u GravityWinz --password-stdin
