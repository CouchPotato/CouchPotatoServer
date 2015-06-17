'use strict';

module.exports = function(grunt){
	require('jit-grunt')(grunt);
	require('time-grunt')(grunt);

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
				'<%= config.base %>/{,**/}*.js',
				'!<%= config.base %>/static/scripts/vendor/{,**/}*.js'
			]
		},

		// Compiles Sass to CSS and generates necessary files if requested
		sass: {
			options: {
				compass: true,
				update: true,
				sourcemap: 'none'
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
				browsers: ['last 2 versions'],
				remove: false,
				cascade: false
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
				options: {
					keepBreaks: true
				},
				files: {
					'<%= config.css_dest %>': ['<%= config.tmp %>/styles/**/*.css']
				}
			}
		},

		shell: {
			runCouchPotato: {
				command: 'python CouchPotato.py',
				maxBuffer: 1048576
			}
		},

		// COOL TASKS ==============================================================
		watch: {
			scss: {
				files: ['<%= config.base %>/**/*.{scss,sass}'],
				tasks: ['sass:server', 'autoprefixer', 'cssmin']
			},
			js: {
				files: [
					'<%= config.base %>/**/*.js'
				],
				tasks: ['jshint']
			},
			livereload: {
				options: {
					livereload: 35729
				},
				files: [
					'<%= config.css_dest %>'
				]
			}
		},

		concurrent: {
			options: {
				logConcurrentOutput: true
			},
			tasks: ['shell:runCouchPotato', 'watch']
		}

	});

	grunt.registerTask('default', ['sass:server', 'autoprefixer',  'cssmin', 'concurrent']);

};
