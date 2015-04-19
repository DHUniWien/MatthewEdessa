#!/usr/bin/env perl

use strict;
use warnings;
use feature 'say';
use File::Basename;
use JSON qw/decode_json to_json/;
use Text::Tradition;
use Text::Tradition::Directory;
use Text::WagnerFischer::Armenian qw/distance/;
use TryCatch;

binmode STDOUT, ':utf8';
binmode STDERR, ':utf8';

my( $cfile, $db ) = @ARGV;
# Get the name of the tradition from the filename.
my( $base, $path, $suf ) = fileparse( $cfile, qr/\.[^.]*$/ );
# Read in the JSON structure
open(FH, $cfile) or die "Could not open file $cfile: $@";
my $jdata = <FH>;
close FH;
chomp $jdata;
my $cdata = decode_json($jdata);

# Turn it around so the T::T parser can understand it
my $alignment = [];
foreach my $sig ( @{$cdata->{witnesses}} ) {
	push( @{$alignment}, { 'witness' => $sig, 'tokens' => [] } );
}
foreach my $row ( @{$cdata->{table}} ) {
	foreach my $idx ( 0 .. $#$row ) {
		my $token = $row->[$idx]->[0];
		push( @{$alignment->[$idx]->{tokens}}, $token );
	}
}

# Now send it to Text::Tradition.
my $trad = Text::Tradition->new(
	input => 'JSON',
	string => to_json( { alignment => $alignment } ),
	name => "Matthew $base",
	language => 'Armenian'
	);

say $trad->name;

# Add the orthographic relationships where appropriate
my $c = $trad->collation;
my @to_merge;
foreach my $rank (1 .. $c->end->rank - 1) {
	my $row = $cdata->{table}->[$rank-1];
	
	# Get the normalizations at this spot.
	# $DB::single = 1 if $rank == 50;
	my %normalized;
	foreach my $cell ( @$row ) {
		next unless scalar @$cell;
		my $token = $cell->[0];
		if( exists $normalized{$token->{t}} ) {
			my $normal = $normalized{$token->{t}};
			if( $normal ne $token->{n} ) {
				if( index( $token->{lit}, 'num' ) > -1 && $normal !~ /\d/) {
				    # If this is a number, make sure the normalization is a number.
				    $normalized{$token->{t}} = $token->{n};
				} elsif( index( $normal, '.*' ) > -1 ) {
    				# Prefer the normalization that doesn't have a .* in it.
					$normalized{$token->{t}} = $token->{n};
				} elsif( index( $token->{n}, '.*' ) == -1 ) {
					say STDERR sprintf( "Conflicting normalization at rank %d for %s: %s vs. %s",
						$rank, $token->{t}, $token->{n}, $normal );
					# Use the one that has the closer Levenshtein distance.
					my $d1 = distance( $token->{t}, $token->{n} );
					my $d2 = distance( $token->{t}, $normal );
					$normalized{$token->{t}} = $d1 > $d2 ? $normal : $token->{n};
					say STDERR "...using " . $normalized{$token->{t}};
				}
			}
		} else {
			$normalized{$token->{t}} = $token->{n};
		}
	}
	# Now apply them.
	my @readings = sort( $c->readings_at_rank( $rank ) );
	while( @readings ) {
		my $rdg = shift( @readings );
		my $normal = $normalized{$rdg->text};
		foreach my $alt ( @readings ) {
            my $rt = $rdg->text;
            my $at = $alt->text;
            $rt =~ s/\x{55f}//g;
            $at =~ s/\x{55f}//g;
            if( $rt eq $at ) {
                # These are abbreviated the same way. We will collapse them
                # when we are ready to face re-ranking of the graph.
                push( @to_merge, [ $rdg, $alt ]);
                next;
            }
            # Add a punctuation relationship if appropriate
            $rt =~ s/[[:punct:]]+//g;
            $at =~ s/[[:punct:]]+//g;
            if( $rt eq $at ) {
                $c->add_relationship( $rdg, $alt, { type => 'punctuation' } );
                next;
            }
			if( $normal eq $normalized{$alt->text} ) {
				$c->add_relationship( $rdg, $alt, { type => 'orthographic' } );
			}
		}
		if( index( $normal, '.*' ) == -1 ) {
			$rdg->normal_form( $normal );
		}
	}
}
foreach my $pair ( @to_merge ) {
    say STDERR "Merging readings @$pair";
    try {
        $c->merge_readings( @$pair );
    } catch {
        say STDERR "...@$pair apparently already merged."
    }
}


my $dir = Text::Tradition::Directory->new( dsn => "dbi:SQLite:dbname=$db" );
my $scope = $dir->new_scope();
$dir->store( $trad );
