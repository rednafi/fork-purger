<h1>Fork Purger<img src='https://user-images.githubusercontent.com/30027932/137647315-66a6bcf2-7645-46cd-964d-4fe7375be30b.png' align='right' width='128' height='128'></h1>


<strong>>> <i>Delete all of your forked repositories on Github</i> <<</strong>


</div>

![python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![github_actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)


## Installation

* Install using pip:

    ```
    pip install fork-purger
    ```

## Exploration

* Create and collect your Github [user access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token).

* Inspect the `--help` menu. Run:

    ```
    fork-purger --help
    ```

    This will print the following:

    ```
    +-+-+-+-+ +-+-+-+-+-+-+
    |F|o|r|k| |P|u|r|g|e|r|
    +-+-+-+-+ +-+-+-+-+-+-+

    Usage: fork-purger [OPTIONS]

    Options:
    --username TEXT       Your Github username.  [required]
    --token TEXT          Your Github access token with delete permission.
                            [required]
    --debug / --no-debug  See full traceback in case of HTTP error.
    --delete              Delete the forked repos.
    --help                Show this message and exit.
    ```

* By default, `fork-purger` runs in dry mode and doesn't do anything other than just listing the repositories about to be deleted. Run:

    ```
    fork-purger --username <gh-username> --token <gh-access-token>
    ```

    You'll see the following output:

    ```
    +-+-+-+-+ +-+-+-+-+-+-+
    |F|o|r|k| |P|u|r|g|e|r|
    +-+-+-+-+ +-+-+-+-+-+-+

    These forks will be deleted:
    =============================

    https://api.github.com/repos/<gh-username>/ddosify
    https://api.github.com/repos/<gh-username>/delete-github-forks
    https://api.github.com/repos/<gh-username>/dependabot-core
    https://api.github.com/repos/<gh-username>/fork-purger
    ```

* To delete the listed repositories, run the CLI with the `--delete` flag:

    ```
    fork-purger --username <gh-username> --token <gh-access-token> --delete
    ```

    The output should look similar to this:
    ```
    +-+-+-+-+ +-+-+-+-+-+-+
    |F|o|r|k| |P|u|r|g|e|r|
    +-+-+-+-+ +-+-+-+-+-+-+

    Deleting forked repos:
    =======================

    Deleting... https://api.github.com/repos/<gh-username>/ddosify
    Deleting... https://api.github.com/repos/<gh-username>/delete-github-forks
    Deleting... https://api.github.com/repos/<gh-username>/dependabot-core
    Deleting... https://api.github.com/repos/<gh-username>/fork-purger
    ```

* In case of exceptions, if you need more information, you can run the CLI with the `--debug` flag. This will print out the Python stack trace on the stdout.

    ```
    fork-purger --username <gh-username> --token <gh-access-token> --delete --debug
    ```

<div align="center">
<i> ✨ 🍰 ✨ </i>
</div>
