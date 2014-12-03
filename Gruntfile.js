'use strict';

module.exports = function(grunt){

	// Configurable paths
	var config = {
		tmp: '.tmp',
		base: 'couchpotato'
	};

	grunt.initConfig({

		// Project settings
		config: config,

		// Make sure code styles are up to par and there are no obvious mistakes
		jshint: {
			options: {
				reporter: require('jshint-stylish'),
				unused: false,
				camelcase: false,
				devel: true
			},
			all: [
				'<%= config.base %>/{,**/}*.js'
			]
		},

		// Compiles Sass to CSS and generates necessary files if requested
		sass: {
			options: {
				compass: true
			},
			dist: {
				files: [{
					expand: true,
					cwd: '<%= config.base %>/styles',
					src: ['*.scss'],
					dest: '<%= config.tmp %>/styles',
					ext: '.css'
				}]
			},
			server: {
				files: [{
					expand: true,
					cwd: '<%= config.base %>/',
					src: ['**/*.scss'],
					dest: '<%= config.tmp %>/styles',
					ext: '.css'
				}]
			}
		},

		// Add vendor prefixed styles
		autoprefixer: {
			options: {
				browsers: ['> 1%', 'Android >= 2.1', 'Chrome >= 21', 'Explorer >= 7', 'Firefox >= 17', 'Opera >= 12.1', 'Safari >= 6.0']
			},
			dist: {
				files: [{
					expand: true,
					cwd: '<%= config.tmp %>/styles/',
					src: '{,**/}*.css',
					dest: '<%= config.tmp %>/styles/'
				}]
			}
		},

		concat: {
			options: {
				separator: ''
			},
			dist: {
				src: ['<%= config.tmp %>/styles/**/*.css'],
				dest: '<%= config.tmp %>/test.css'
			}
		},

		// COOL TASKS ==============================================================
		watch: {
			scss: {
				files: ['**/*.{scss,sass}'],
				tasks: ['sass:server', 'autoprefixer', 'concat'],
				options: {
					'livereload': true
				}
			},
			js: {
				files: [
                    '<%= config.base %>/scripts/**/*.js'
                ],
				tasks: ['jshint'],
				options: {
					'livereload': true
				}
			},
			livereload: {
				options: {
					livereload: 35729
				},
				files: [
					'<%= config.base %>/{,*/}*.html',
					'<%= config.tmp %>/styles/{,*/}*.css',
					'<%= config.base %>/react/{,*/}*.js',
					'<%= config.base %>/images/{,*/}*'
				]
			}
		},

		concurrent: {
			options: {
				logConcurrentOutput: true
			},
			tasks: ['sass:server', 'watch']
		}

	});

	grunt.loadNpmTasks('grunt-contrib-jshint');
	//grunt.loadNpmTasks('grunt-contrib-uglify');
	grunt.loadNpmTasks('grunt-contrib-sass');
	//grunt.loadNpmTasks('grunt-contrib-cssmin');
	grunt.loadNpmTasks('grunt-contrib-watch');
	grunt.loadNpmTasks('grunt-autoprefixer');
	grunt.loadNpmTasks('grunt-concurrent');
	grunt.loadNpmTasks('grunt-contrib-concat');

	grunt.registerTask('default', ['sass', 'concurrent']);

};
