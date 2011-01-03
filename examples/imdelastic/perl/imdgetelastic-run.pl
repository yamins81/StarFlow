#!/usr/bin/perl
use Cwd;
use File::Path;
use sigtrap 'handler', \&cleanup , 'error-signals' ;
$SIG{PIPE}=\&trap; $SIG{QUIT}=\&trap; $SIG{INT}=\&trap; $SIG{STOP}=\&trap; $SIG{HUP}=\&trap;

sub trap
{
        debug( "Stop!" ) ;
        &cleanup ;
}

my ( $input_file , $r_cut , $lj_eps , $lj_sigma , $lindef_inter , $lindef_xx , $lindef_yy , $lindef_zz , $output_file ) = @ARGV ;

if( defined( $input_file ) && ( -f $input_file  ) && defined( $output_file ) )
{
open IN , $input_file ;
open OUT , ">$output_file" ;
while( $line = <IN> )
{
	$line =~ s/R_CUT/$r_cut/g ;
	$line =~ s/LJ_EPSILON/$lj_eps/g ;
	$line =~ s/LJ_SIGMA/$lj_sigma/g ;
	$line =~ s/LINDEF_INTERVAL/$lindef_inter/g ;
	$line =~ s/LINDEF_XX/$lindef_xx/g ;
	$line =~ s/LINDEF_YY/$lindef_yy/g ;
	$line =~ s/LINDEF_ZZ/$lindef_zz/g ;
	print OUT $line ;
}
close IN ;
close OUT ;
}
else
{
	die "Usage: $0 input_file r_cut lj_eps lj_sigma lindef_inter lindef_xx lindef_yy lindef_zz output_file\n" ;
}

sub cleanup
{
	&debug( "removing $cwd" );
	$cwd = getcwd ;
	rmtree($cwd) ;
	`echo "cleanup in imdgetelastic" >> /home/gpserver/iran`;
	exit;
}

sub debug
{
        print STDERR join( "\n" , @_ ) . "\n" ;
        open FILE , ">>myError.log" ;
        print FILE join( "\n" , @_ ) . "\n" ;
        close FILE ;
}

