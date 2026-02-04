def remote = [:]

pipeline {

    agent any

    environment {
        user = credentials('track_adapt_wiki_user')
        host = credentials('track_adapt_wiki_host')
        name = credentials('track_adapt_wiki_host')
        ssh_key = credentials('track_adapt_wiki')
    }

    stages {
        stage('SSH Connection Setup') {
            steps {
                script {
                    // Set up remote SSH connection parameters
                    remote.allowAnyHosts = true
                    remote.identityFile = ssh_key
                    remote.user = user
                    remote.name = name
                    remote.host = host
                }
            }
        }

        stage('Update Code') {
            steps {
                script {
                    try {
                        sshCommand remote: remote, command: """
                            cd /opt/goodall/
                            git fetch --all
                            git checkout main
                            git pull origin main
                        """
                    } catch (Exception e) {
                        echo "Git Pull Error: ${e.message}"
                        error("Failed to update code: ${e.message}")
                    }
                }
            }
        }

        stage('Install Python Dependencies') {
            steps {
                script {
                    try {
                        sshCommand remote: remote, command: """
                            cd /opt/goodall/src/mysite
                            conda activate goodall
                            pip install -r requirements.txt
                        """
                    } catch (Exception e) {
                        echo "Dependencies Installation Error: ${e.message}"
                        error("Failed to install dependencies: ${e.message}")
                    }
                }
            }
        }

        stage('Run Migrations') {
            steps {
                script {
                    try {
                        sshCommand remote: remote, command: """
                            cd /opt/goodall/src/mysite
                            conda activate goodall
                            python manage.py migrate --noinput
                        """
                    } catch (Exception e) {
                        echo "Migration Error: ${e.message}"
                        error("Failed to run migrations: ${e.message}")
                    }
                }
            }
        }

        stage('Collect Static Files') {
            steps {
                script {
                    try {
                        sshCommand remote: remote, command: """
                            cd /opt/goodall/src/mysite
                            conda activate goodall
                            python manage.py collectstatic --noinput
                        """
                    } catch (Exception e) {
                        echo "Collect Static Error: ${e.message}"
                        error("Failed to collect static files: ${e.message}")
                    }
                }
            }
        }

        stage('Restart Application') {
            steps {
                script {
                    try {
                        sshCommand remote: remote, command: """
                            # Restart Apache server
                            sudo systemctl reload apache2
                        """
                    } catch (Exception e) {
                        echo "Restart Error: ${e.message}"
                        error("Failed to restart application: ${e.message}")
                    }
                }
            }
        }
    }
    
    post {
        failure {
            script {
                echo 'Deployment failed!'
                // Add notification here (email, Slack, etc.)
            }
        }

        success {
            script {
                echo 'Deployment successful!'
                // Add notification here (email, Slack, etc.)
            }
        }
    }
}
