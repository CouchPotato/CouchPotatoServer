'use strict';

module.exports = function(grunt){

	// Configurable paths
	var config = {
		tmp: '.tmp',
		base: 'couchpotato',
		css_dest: 'couchpotato/static/style/combined.min.css'
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
				compass: true,
				update: true
			},
			server: {
				files: [{
					expand: true,
					cwd: '<%= config.base %>/',
					src: ['**/*.scss'],
					dest: '<%= config.tmp %>/styles/',
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

		cssmin: {
			dist: {
				files: {
					'<%= config.css_dest %>': ['<%= config.tmp %>/styles/**/*.css']
				}
			}
		},

		// COOL TASKS ==============================================================
		watch: {
			scss: {
				files: ['<%= config.base %>/**/*.{scss,sass}'],
				tasks: ['sass:server', 'autoprefixer', 'cssmin'],
				options: {
					'livereload': true
				}
			},
			js: {
				files: [
                    '<%= config.base %>/**/*.js'
                ],
				tasks: ['jshint', 'uglify'],
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
					'<%= config.base %>/images/{,*/}*'
				]
			}
		},

		concurrent: {
			options: {
				logConcurrentOutput: true
			},
			tasks: ['sass:server', 'autoprefixer', 'cssmin', 'watch']
		}

	});

	grunt.loadNpmTasks('grunt-contrib-jshint');
	//grunt.loadNpmTasks('grunt-contrib-uglify');
	grunt.loadNpmTasks('grunt-contrib-sass');
	grunt.loadNpmTasks('grunt-contrib-cssmin');
	grunt.loadNpmTasks('grunt-contrib-watch');
	grunt.loadNpmTasks('grunt-autoprefixer');
	grunt.loadNpmTasks('grunt-concurrent');

	grunt.registerTask('default', ['concurrent']);

};
