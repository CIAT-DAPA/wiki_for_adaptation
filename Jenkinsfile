def remote = [:]

pipeline {

    agent any

    environment {
        user = credentials('wiki_adaptation_user')
        host = credentials('wiki_adaptation_host')
        name = credentials('wiki_adaptation_name')
        ssh_key = credentials('wiki_adaptation_key')
        app_path = credentials('wiki_adaptation_app_path')
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
                            cd ${app_path}
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
                            cd ${app_path}/src/mysite
                            source ../../../env/bin/activate
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
                            cd ${app_path}/src/mysite
                            source ../../../env/bin/activate
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
                            cd ${app_path}/src/mysite
                            source ../../../env/bin/activate
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
