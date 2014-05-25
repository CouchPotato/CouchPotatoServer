# Contributing to CouchPotatoServer

1. [Contributing](#contributing)
2. [Submitting an Issue](#issues)
3. [Submitting a Pull Request](#pull-requests)

## Contributing
Thank you for your interest in contributing to CouchPotato. There are several ways to help out, even if you've never worked on an open source project before.
If you've found a bug or want to request a feature, you can report it by [posting an issue](https://github.com/RuudBurger/CouchPotatoServer/issues/new) - be sure to read the [guidelines](#issues) first!
If you want to contribute your own work, please read the [guidelines](#pull-requests) for submitting a pull request.
Lastly, for anything related to CouchPotato, feel free to stop by the [forum](http://couchpota.to/forum/) or the [#couchpotato](http://webchat.freenode.net/?channels=couchpotato) IRC channel at irc.freenode.net.

## Issues
Issues are intended for reporting bugs and weird behaviour or suggesting improvements to CouchPotatoServer.
Before you submit an issue, please go through the following checklist:
 * Search through existing issues (*including closed issues!*) first: you might be able to get your answer there.
 * Double check your issue manually, because it could be an external issue. 
 * Post logs with your issue: Without seeing what is going on, the developers can't reproduce the error.
 * Check the logs yourself before submitting them. Obvious errors like permission or HTTP errors are often not related to CouchPotato.
 * What movie and quality are you searching for?
 * What are your settings for the specific problem?
 * What providers are you using? (While your logs include these, scanning through hundreds of lines of logs isn't our hobby)
 * Post the logs from the *config* directory, please do not copy paste the UI. Use pastebin to store these logs!
 * Give a short step by step of how to reproduce the error.
 * What hardware / OS are you using and what are its limitations? For example: NAS can be slow and maybe have a different version of python installed than when you use CP on OS X or Windows.
 * Your issue might be marked with the "can't reproduce" tag. Don't ask why your issue was closed if it says so in the tag.
 * If you're running on a NAS (QNAP, Austor, Synology etc.) with pre-made packages, make sure these are set up to use our source repository (RuudBurger/CouchPotatoServer) and nothing else!

The more relevant information you provide, the more likely that your issue will be resolved.

## Pull Requests
Pull requests are intended for contributing code or documentation to the project. Before you submit a pull request, consider the following:
 * Make sure your pull request is made for the *develop* branch (or relevant feature branch).
 * Have you tested your PR? If not, why?
 * Does your PR have any limitations we should know of?
 * Is your PR up-to-date with the branch you're trying to push into?
