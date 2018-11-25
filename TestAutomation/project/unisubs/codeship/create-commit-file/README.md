Tiny docker container to create the commit.py file during our codeship build

Usage:
- Codeship checks out the unisubs repository and makes that the CWD during the build
- Mount that at /repository
- Use any command you want, the args are ignored
