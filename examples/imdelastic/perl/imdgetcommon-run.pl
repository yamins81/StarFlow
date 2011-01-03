#!/usr/bin/perl
use File::Path;
use Cwd;
use sigtrap 'handler', \&cleanup , 'error-signals' ;
$SIG{PIPE}=\&trap; $SIG{QUIT}=\&trap; $SIG{INT}=\&trap; $SIG{STOP}=\&trap; $SIG{HUP}=\&trap;

sub trap
{
        debug( "Stop!" ) ;
        &cleanup ;
}

my ( $input_file , $coordname , $maxsteps , $timestep , $pbc_x , $pbc_y , $pbc_z , $boxname , $eng_int , $checkpt , $starttemp , $output_file ) = @ARGV ;

if( defined( $input_file ) && ( -f $input_file  ) && defined( $output_file ) && ( -f $boxname ) )
{
open IN , $boxname ;
my $boxcontent = join( "" , <IN> ) ;
close IN ;
open IN , $input_file ;
open OUT , ">$output_file" ;
while( $line = <IN> )
{
	$line =~ s/COORDNAME/$coordname/g ;
	$line =~ s/MAXSTEPS/$maxsteps/g ;
	$line =~ s/TIMESTEP/$timestep/g ;
	$line =~ s/PBC_X/$pbc_x/g ;
	$line =~ s/PBC_Y/$pbc_y/g ;
	$line =~ s/PBC_Z/$pbc_z/g ;
	$line =~ s/BOX/$boxcontent/g ;
	$line =~ s/ENG_INT/$eng_int/g ;
	$line =~ s/CHECKPT/$checkpt/g ;
	$line =~ s/STARTTEMP/$starttemp/g ;
	print OUT $line ;
}
close IN ;
close OUT ;
}
else
{
	die "Usage: $0 input_file coordname maxsteps timestep pbc_x pbc_y pbc_z boxname eng_int checkpt starttemp output_file\n" ;
}

sub cleanup
{
	&debug( "removing $cwd" ) ;
	$cwd = getcwd ;
	rmtree($cwd) ;
	`echo "cleanup in imdgetcommon" >> /home/gpserver/iran`;
	exit;
}

sub debug
{
        print STDERR join( "\n" , @_ ) . "\n" ;
        open FILE , ">>myError.log" ;
        print FILE join( "\n" , @_ ) . "\n" ;
        close FILE ;
}

